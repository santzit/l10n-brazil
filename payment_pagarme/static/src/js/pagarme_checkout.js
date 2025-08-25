/** @odoo-module */

import checkoutForm from 'payment.checkout_form';
import manageForm from 'payment.manage_form';

const pagarmeTransparentCheckoutMixin = {

    /**
     * Override payment processing to handle Pagar.me transparent checkout
     * 
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} provider - The provider of the payment option's provider
     * @param {number} paymentOptionId - The id of the payment option handling the transaction
     * @param {string} flow - The online payment flow of the transaction
     * @return {Promise}
     */
    async _processPayment(provider, paymentOptionId, flow) {
        console.log('Pagar.me: _processPayment called with:', { provider, paymentOptionId, flow });
        
        if (provider !== 'pagarme' || flow === 'token') {
            console.log('Pagar.me: delegating to super for provider:', provider, 'flow:', flow);
            return this._super(...arguments); // Tokens and other providers are handled by generic flow
        }

        console.log('Pagar.me: Starting payment processing for provider ID:', paymentOptionId);

        // Validate form before processing
        console.log('Pagar.me: Validating form...');
        if (!this._validatePagarmeForm(paymentOptionId)) {
            console.error('Pagar.me: Form validation failed');
            this._displayError('Formulário Inválido', 'Por favor, verifique os dados do cartão e tente novamente.');
            return Promise.reject("Invalid form data");
        }
        console.log('Pagar.me: Form validation successful');

        // Show loading state
        console.log('Pagar.me: Showing loading state...');
        this._displayLoading();

        try {
            console.log('Pagar.me: Creating transaction with route:', this.txContext.transactionRoute);
            console.log('Pagar.me: Transaction context:', this.txContext);
            
            // Create transaction and get processing values with timeout
            const transactionParams = this._prepareTransactionRouteParams('pagarme', paymentOptionId, 'direct');
            console.log('Pagar.me: Transaction route params:', transactionParams);
            
            const processingValues = await Promise.race([
                this._rpc({
                    route: this.txContext.transactionRoute,
                    params: transactionParams,
                }),
                new Promise((_, reject) => 
                    setTimeout(() => reject(new Error('Transaction creation timeout after 30 seconds')), 30000)
                )
            ]);
            console.log('Pagar.me: Transaction created successfully:', processingValues);

            // Prepare payment data from form
            console.log('Pagar.me: Preparing payment data from form...');
            const paymentData = this._preparePagarmePaymentData(paymentOptionId);
            console.log('Pagar.me: Payment data prepared:', {
                ...paymentData,
                card_number: paymentData.card_number ? '****' + paymentData.card_number.slice(-4) : 'missing',
                card_cvv: paymentData.card_cvv ? '***' : 'missing'
            });

            // Prepare request to Pagar.me payment endpoint
            const paymentRequest = {
                'provider_id': paymentOptionId,
                'reference': processingValues.reference,
                'converted_amount': processingValues.converted_amount,
                'currency_id': processingValues.currency_id,
                'partner_id': processingValues.partner_id,
                'payment_data': paymentData,
                'access_token': processingValues.access_token,
            };
            console.log('Pagar.me: Sending payment request to /payment/pagarme/payment:', {
                ...paymentRequest,
                payment_data: {
                    ...paymentRequest.payment_data,
                    card_number: paymentRequest.payment_data.card_number ? '****' + paymentRequest.payment_data.card_number.slice(-4) : 'missing',
                    card_cvv: paymentRequest.payment_data.card_cvv ? '***' : 'missing'
                }
            });

            // Process payment through Pagar.me API with timeout
            const paymentResult = await Promise.race([
                this._rpc({
                    route: '/payment/pagarme/payment',
                    params: paymentRequest,
                }),
                new Promise((_, reject) => 
                    setTimeout(() => reject(new Error('Payment processing timeout after 60 seconds')), 60000)
                )
            ]);
            console.log('Pagar.me: Payment request completed with result:', paymentResult);

            if (paymentResult && paymentResult.status === 'success') {
                console.log('Pagar.me: Payment successful, redirecting to /payment/status');
                // Redirect to payment status page
                window.location = '/payment/status';
            } else {
                const errorMessage = paymentResult?.message || 'Falha no processamento do pagamento';
                console.error('Pagar.me: Payment failed with message:', errorMessage);
                this._displayError('Erro no Pagamento', errorMessage);
            }

        } catch (error) {
            console.error('Pagar.me: Payment processing error:', error);
            console.error('Pagar.me: Error details:', {
                message: error.message,
                type: error.type,
                data: error.data,
                stack: error.stack
            });
            
            let errorMessage = 'Erro ao processar pagamento. Tente novamente.';
            if (error.message && error.message.includes('timeout')) {
                errorMessage = 'Timeout na comunicação. Verifique sua conexão e tente novamente.';
            } else if (error.data && error.data.message) {
                errorMessage = error.data.message;
            }
            
            this._displayError('Erro no Pagamento', errorMessage);
        } finally {
            console.log('Pagar.me: Hiding loading state...');
            this._hideLoading();
        }
    },

    /**
     * Initialize Pagar.me form when mounted
     * 
     * @override method from payment.payment_form_mixin
     * @private
     * @param {number} paymentOptionId - The id of the payment option handling the transaction
     * @return {Promise}
     */
    async _prepareInlineForm(paymentOptionId) {
        console.log('Pagar.me: _prepareInlineForm called with paymentOptionId:', paymentOptionId);
        
        // Check if this is a Pagar.me provider
        const providerInput = this.$(`input[name="provider_code"][value="pagarme"]`);
        console.log('Pagar.me: Provider input found:', providerInput.length > 0);
        console.log('Pagar.me: Looking for provider radio with ID:', paymentOptionId);
        
        // Check if the current payment option is Pagar.me
        const paymentOptionInput = this.$(`input[name="payment_option_id"][value="${paymentOptionId}"]`);
        console.log('Pagar.me: Payment option input found:', paymentOptionInput.length > 0);
        
        if (paymentOptionInput.length > 0) {
            const providerCode = paymentOptionInput.data('provider-code');
            console.log('Pagar.me: Provider code from payment option:', providerCode);
            
            if (providerCode !== 'pagarme') {
                console.log('Pagar.me: Not a Pagar.me provider, delegating to super');
                return this._super(...arguments);
            }
        } else if (providerInput.length === 0) {
            console.log('Pagar.me: No Pagar.me provider input found, delegating to super');
            return this._super(...arguments);
        }

        console.log('Pagar.me: This is a Pagar.me provider, proceeding with initialization');
        
        // Look for the payment container
        const container = this.$(`#o_pagarme_payment_container_${paymentOptionId}`);
        console.log('Pagar.me: Looking for container with ID:', `#o_pagarme_payment_container_${paymentOptionId}`);
        console.log('Pagar.me: Container found:', container.length > 0);
        
        if (container.length === 0) {
            console.warn('Pagar.me: Payment container not found for provider ID:', paymentOptionId);
            console.warn('Pagar.me: Available containers in DOM:', this.$('[id*="pagarme"]').map(function() { return this.id; }).get());
            console.warn('Pagar.me: All payment containers:', this.$('[id*="payment_container"]').map(function() { return this.id; }).get());
            return Promise.resolve();
        }

        console.log('Pagar.me: Container found, initializing form features...');
        // Initialize form features
        this._initializePagarmeForm(paymentOptionId);

        return Promise.resolve();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Initialize Pagar.me form features
     * @private
     * @param {number} paymentOptionId
     */
    _initializePagarmeForm: function (paymentOptionId) {
        const container = this.$(`#o_pagarme_payment_container_${paymentOptionId}`);
        
        // Populate year options
        this._populateYearOptions(container);
        
        // Initialize input masks
        this._initializeInputMasks(container);
        
        // Load installments
        this._loadInstallments(container);
    },

    /**
     * Populate year options for card expiry
     * @private
     * @param {jQuery} container
     */
    _populateYearOptions: function (container) {
        const yearSelect = container.find('select[name="pagarme_card_exp_year"]');
        if (yearSelect.length === 0) return;
        
        const currentYear = new Date().getFullYear();
        yearSelect.empty().append('<option value="">Ano</option>');
        
        for (let i = 0; i <= 10; i++) {
            const year = currentYear + i;
            yearSelect.append($('<option>', {
                value: year.toString().slice(-2),
                text: year
            }));
        }
    },

    /**
     * Initialize input masks
     * @private
     * @param {jQuery} container
     */
    _initializeInputMasks: function (container) {
        // Card number mask
        container.find('input[name="pagarme_card_number"]').on('input', function () {
            let value = this.value.replace(/\D/g, '');
            value = value.replace(/(\d{4})(?=\d)/g, '$1 ');
            this.value = value.substr(0, 19);
        });

        // Document mask (CPF/CNPJ)
        container.find('input[name="pagarme_customer_document"]').on('input', function () {
            let value = this.value.replace(/\D/g, '');
            
            if (value.length <= 11) {
                // CPF format
                value = value.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
            } else {
                // CNPJ format
                value = value.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
            }
            this.value = value;
        });

        // CVV mask
        container.find('input[name="pagarme_card_cvv"]').on('input', function () {
            this.value = this.value.replace(/\D/g, '').substr(0, 4);
        });
    },

    /**
     * Load available installments
     * @private
     * @param {jQuery} container
     */
    _loadInstallments: function (container) {
        const amount = parseFloat(this.txContext.amount);
        if (!amount) return;

        this._rpc({
            route: '/payment/pagarme/get_installments',
            params: { amount: amount }
        }).then((result) => {
            if (result.status === 'success') {
                const installmentsSelect = container.find('select[name="pagarme_installments"]');
                installmentsSelect.empty();
                
                result.installments.forEach((option) => {
                    installmentsSelect.append($('<option>', {
                        value: option.installments,
                        text: option.label
                    }));
                });
            }
        }).catch((error) => {
            console.error('Error loading installments:', error);
        });
    },

    /**
     * Validate Pagar.me form data
     * @private
     * @param {number} paymentOptionId
     * @returns {boolean}
     */
    _validatePagarmeForm: function (paymentOptionId) {
        console.log('Pagar.me: Starting form validation for provider ID:', paymentOptionId);
        
        // First, let's debug what's in the DOM
        console.log('Pagar.me: All Pagar.me containers in DOM:', this.$('[id*="pagarme"]').map(function() { 
            return { id: this.id, visible: $(this).is(':visible'), hasClass: this.className }; 
        }).get());
        console.log('Pagar.me: All payment containers in DOM:', this.$('[id*="payment_container"]').map(function() { 
            return { id: this.id, visible: $(this).is(':visible'), hasClass: this.className }; 
        }).get());
        
        const container = this.$(`#o_pagarme_payment_container_${paymentOptionId}`);
        console.log('Pagar.me: Looking for container with selector:', `#o_pagarme_payment_container_${paymentOptionId}`);
        console.log('Pagar.me: Container found:', container.length > 0);
        
        if (container.length === 0) {
            console.error('Pagar.me: payment container not found:', paymentOptionId);
            console.error('Pagar.me: Available payment forms in DOM:');
            this.$('[class*="payment"]').each(function(index) {
                console.error(`  - ${index}: ID="${this.id}", Class="${this.className}"`);
            });
            return false;
        }
        console.log('Pagar.me: Found payment container, proceeding with validation');
        console.log('Pagar.me: Container is visible:', container.is(':visible'));
        console.log('Pagar.me: Container has inputs:', container.find('input').length);

        let isValid = true;
        let invalidFields = [];

        // Validate required fields
        const requiredFields = container.find('input[required], select[required]');
        console.log('Pagar.me: Found', requiredFields.length, 'required fields');
        
        requiredFields.each(function () {
            const field = $(this);
            const fieldName = this.name || this.id || 'unknown';
            const value = this.value || '';
            console.log('Pagar.me: Checking required field:', fieldName, 'value:', value.length > 0 ? '[HAS_VALUE]' : '[EMPTY]');
            
            if (!value.trim()) {
                isValid = false;
                invalidFields.push(fieldName);
                field.addClass('is-invalid');
                console.warn('Pagar.me: Required field is empty:', fieldName);
            } else {
                field.removeClass('is-invalid');
                console.log('Pagar.me: Required field validated:', fieldName);
            }
        });

        // Validate card number
        const cardNumberElement = container.find('input[name="pagarme_card_number"]');
        console.log('Pagar.me: Card number input found:', cardNumberElement.length > 0);
        const cardNumberValue = cardNumberElement.val() || '';
        const cardNumber = cardNumberValue.replace(/\s/g, '');
        console.log('Pagar.me: Validating card number (length:', cardNumber.length, ')');
        if (!this._validateCardNumber(cardNumber)) {
            isValid = false;
            invalidFields.push('card_number');
            cardNumberElement.addClass('is-invalid');
            console.error('Pagar.me: Card number validation failed');
        } else {
            cardNumberElement.removeClass('is-invalid');
            console.log('Pagar.me: Card number validation successful');
        }

        // Validate document
        const documentElement = container.find('input[name="pagarme_customer_document"]');
        console.log('Pagar.me: Document input found:', documentElement.length > 0);
        const documentValue = documentElement.val() || '';
        const document = documentValue.replace(/\D/g, '');
        console.log('Pagar.me: Validating document (length:', document.length, ')');
        if (!this._validateDocument(document)) {
            isValid = false;
            invalidFields.push('customer_document');
            documentElement.addClass('is-invalid');
            console.error('Pagar.me: Document validation failed');
        } else {
            documentElement.removeClass('is-invalid');
            console.log('Pagar.me: Document validation successful');
        }

        console.log('Pagar.me: Form validation completed. Valid:', isValid, 'Invalid fields:', invalidFields);
        return isValid;
    },

    /**
     * Validate card number using Luhn algorithm
     * @private
     * @param {string} cardNumber
     * @returns {boolean}
     */
    _validateCardNumber: function (cardNumber) {
        if (!cardNumber || typeof cardNumber !== 'string' || cardNumber.length < 13) {
            return false;
        }
        
        let sum = 0;
        let alternate = false;
        
        for (let i = cardNumber.length - 1; i >= 0; i--) {
            let n = parseInt(cardNumber.charAt(i), 10);
            
            if (isNaN(n)) {
                return false;
            }
            
            if (alternate) {
                n *= 2;
                if (n > 9) {
                    n = (n % 10) + 1;
                }
            }
            
            sum += n;
            alternate = !alternate;
        }
        
        return (sum % 10) === 0;
    },

    /**
     * Validate Brazilian document (CPF/CNPJ)
     * @private
     * @param {string} document
     * @returns {boolean}
     */
    _validateDocument: function (document) {
        if (!document || typeof document !== 'string') {
            return false;
        }
        
        if (document.length === 11) {
            return this._validateCPF(document);
        } else if (document.length === 14) {
            return this._validateCNPJ(document);
        }
        
        return false;
    },

    /**
     * Validate CPF
     * @private
     * @param {string} cpf
     * @returns {boolean}
     */
    _validateCPF: function (cpf) {
        if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) {
            return false;
        }
        
        let sum = 0;
        for (let i = 0; i < 9; i++) {
            sum += parseInt(cpf.charAt(i)) * (10 - i);
        }
        let remainder = (sum * 10) % 11;
        if (remainder === 10 || remainder === 11) remainder = 0;
        if (remainder !== parseInt(cpf.charAt(9))) return false;
        
        sum = 0;
        for (let i = 0; i < 10; i++) {
            sum += parseInt(cpf.charAt(i)) * (11 - i);
        }
        remainder = (sum * 10) % 11;
        if (remainder === 10 || remainder === 11) remainder = 0;
        if (remainder !== parseInt(cpf.charAt(10))) return false;
        
        return true;
    },

    /**
     * Validate CNPJ
     * @private
     * @param {string} cnpj
     * @returns {boolean}
     */
    _validateCNPJ: function (cnpj) {
        if (cnpj.length !== 14 || /^(\d)\1{13}$/.test(cnpj)) {
            return false;
        }
        
        let length = cnpj.length - 2;
        let numbers = cnpj.substring(0, length);
        let digits = cnpj.substring(length);
        let sum = 0;
        let pos = length - 7;
        
        for (let i = length; i >= 1; i--) {
            sum += numbers.charAt(length - i) * pos--;
            if (pos < 2) pos = 9;
        }
        
        let result = sum % 11 < 2 ? 0 : 11 - sum % 11;
        if (result !== parseInt(digits.charAt(0))) return false;
        
        length = length + 1;
        numbers = cnpj.substring(0, length);
        sum = 0;
        pos = length - 7;
        
        for (let i = length; i >= 1; i--) {
            sum += numbers.charAt(length - i) * pos--;
            if (pos < 2) pos = 9;
        }
        
        result = sum % 11 < 2 ? 0 : 11 - sum % 11;
        if (result !== parseInt(digits.charAt(1))) return false;
        
        return true;
    },

    /**
     * Prepare payment data from form
     * @private
     * @param {number} paymentOptionId
     * @returns {object}
     */
    _preparePagarmePaymentData: function (paymentOptionId) {
        const container = this.$(`#o_pagarme_payment_container_${paymentOptionId}`);
        
        // Helper function to safely get field values
        const getFieldValue = (selector) => {
            const element = container.find(selector);
            return element.length > 0 ? (element.val() || '') : '';
        };
        
        return {
            customer_name: getFieldValue('input[name="pagarme_customer_name"]'),
            customer_document: getFieldValue('input[name="pagarme_customer_document"]').replace(/\D/g, ''),
            card_number: getFieldValue('input[name="pagarme_card_number"]').replace(/\s/g, ''),
            card_holder_name: getFieldValue('input[name="pagarme_card_holder_name"]'),
            card_exp_month: getFieldValue('select[name="pagarme_card_exp_month"]'),
            card_exp_year: getFieldValue('select[name="pagarme_card_exp_year"]'),
            card_cvv: getFieldValue('input[name="pagarme_card_cvv"]'),
            installments: getFieldValue('select[name="pagarme_installments"]') || '1',
        };
    },

    /**
     * Display loading state
     * @private
     */
    _displayLoading: function () {
        console.log('Pagar.me: Setting loading state');
        this.$('.o_pagarme_payment_form').addClass('o_loading');
        // Also disable the pay button to prevent multiple clicks
        this.$('button[name="o_payment_submit_button"]').prop('disabled', true).text('Processando...');
    },

    /**
     * Hide loading state  
     * @private
     */
    _hideLoading: function () {
        console.log('Pagar.me: Removing loading state');
        this.$('.o_pagarme_payment_form').removeClass('o_loading');
        // Re-enable the pay button
        this.$('button[name="o_payment_submit_button"]').prop('disabled', false).text('Pagar');
    },

    /**
     * Display error message
     * @private
     * @param {string} title
     * @param {string} message
     */
    _displayError: function (title, message) {
        this.displayNotification({
            type: 'danger',
            title: title,
            message: message,
        });
    },
};

checkoutForm.include(pagarmeTransparentCheckoutMixin);
manageForm.include(pagarmeTransparentCheckoutMixin);