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
        if (provider !== 'pagarme' || flow === 'token') {
            return this._super(...arguments); // Tokens and other providers are handled by generic flow
        }

        // Validate form before processing
        if (!this._validatePagarmeForm(paymentOptionId)) {
            return Promise.reject("Invalid form data");
        }

        // Show loading state
        this._displayLoading();

        try {
            // Create transaction and get processing values
            const processingValues = await this._rpc({
                route: this.txContext.transactionRoute,
                params: this._prepareTransactionRouteParams('pagarme', paymentOptionId, 'direct'),
            });

            // Prepare payment data from form
            const paymentData = this._preparePagarmePaymentData(paymentOptionId);

            // Process payment through Pagar.me API
            const paymentResult = await this._rpc({
                route: '/payment/pagarme/payment',
                params: {
                    'provider_id': paymentOptionId,
                    'reference': processingValues.reference,
                    'converted_amount': processingValues.converted_amount,
                    'currency_id': processingValues.currency_id,
                    'partner_id': processingValues.partner_id,
                    'payment_data': paymentData,
                    'access_token': processingValues.access_token,
                },
            });

            if (paymentResult.status === 'success') {
                // Redirect to payment status page
                window.location = '/payment/status';
            } else {
                this._displayError('Erro no Pagamento', paymentResult.message || 'Falha no processamento do pagamento');
            }

        } catch (error) {
            this._displayError('Erro no Pagamento', 'Erro ao processar pagamento. Tente novamente.');
            console.error('Pagar.me payment error:', error);
        } finally {
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
        if (this.$(`input[name="provider_code"][value="pagarme"]`).length === 0) {
            return this._super(...arguments);
        }

        const container = this.$(`#o_pagarme_payment_container_${paymentOptionId}`);
        if (container.length === 0) {
            console.warn('Pagar.me payment container not found for provider ID:', paymentOptionId);
            return Promise.resolve();
        }

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
        const container = this.$(`#o_pagarme_payment_container_${paymentOptionId}`);
        if (container.length === 0) {
            console.error('Pagar.me payment container not found:', paymentOptionId);
            return false;
        }

        let isValid = true;

        // Validate required fields
        container.find('input[required], select[required]').each(function () {
            const field = $(this);
            const value = this.value || '';
            if (!value.trim()) {
                isValid = false;
                field.addClass('is-invalid');
            } else {
                field.removeClass('is-invalid');
            }
        });

        // Validate card number
        const cardNumberElement = container.find('input[name="pagarme_card_number"]');
        const cardNumberValue = cardNumberElement.val() || '';
        const cardNumber = cardNumberValue.replace(/\s/g, '');
        if (!this._validateCardNumber(cardNumber)) {
            isValid = false;
            cardNumberElement.addClass('is-invalid');
        } else {
            cardNumberElement.removeClass('is-invalid');
        }

        // Validate document
        const documentElement = container.find('input[name="pagarme_customer_document"]');
        const documentValue = documentElement.val() || '';
        const document = documentValue.replace(/\D/g, '');
        if (!this._validateDocument(document)) {
            isValid = false;
            documentElement.addClass('is-invalid');
        } else {
            documentElement.removeClass('is-invalid');
        }

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
        this.$('.o_pagarme_payment_form').addClass('o_loading');
    },

    /**
     * Hide loading state  
     * @private
     */
    _hideLoading: function () {
        this.$('.o_pagarme_payment_form').removeClass('o_loading');
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