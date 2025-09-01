/** @odoo-module **/

import checkoutForm from 'payment.checkout_form';
import manageForm from 'payment.manage_form';

const pagarmePaymentMixin = {

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Process payment with Pagar.me using tokenized card data.
     *
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} code - The code of the provider
     * @param {number} providerId - The id of the provider handling the transaction
     * @param {object} processingValues - The processing values of the transaction
     * @return {Promise}
     */
    _processDirectPayment: function (code, providerId, processingValues) {
        if (code !== 'pagarme') {
            return this._super(...arguments);
        }

        console.log('Pagar.me: Processing direct payment for provider ID:', providerId);
        
        // Wait for Pagar.me tokenization to complete
        return this._waitForPagarmeTokenization().then((cardToken) => {
            if (!cardToken) {
                return Promise.reject(new Error('Falha na tokenização do cartão'));
            }

            console.log('Pagar.me: Card tokenized successfully');

            // Process payment with tokenized card data
            return this._rpc({
                route: '/payment/pagarme/payment',
                params: {
                    'reference': processingValues.reference,
                    'card_token': cardToken,
                    'amount': processingValues.amount,
                    'currency': processingValues.currency,
                },
            }).then((result) => {
                if (result.error) {
                    this._displayError('Erro no Pagamento', result.error);
                    return Promise.reject(new Error(result.error));
                } else {
                    console.log('Pagar.me: Payment processed successfully');
                    window.location = '/payment/status';
                    return result;
                }
            }).catch((error) => {
                console.error('Pagar.me: Payment failed:', error);
                this._displayError(
                    'Erro no Pagamento',
                    'Ocorreu um erro ao processar o pagamento. Tente novamente.'
                );
                return Promise.reject(error);
            });
        }).catch((error) => {
            console.error('Pagar.me: Tokenization failed:', error);
            this._displayError(
                'Erro de Tokenização',
                'Falha ao processar dados do cartão. Verifique as informações e tente novamente.'
            );
            return Promise.reject(error);
        });
    },

    /**
     * Wait for Pagar.me tokenization to complete and return the token
     * @private
     * @return {Promise<string>} The card token from Pagar.me
     */
    _waitForPagarmeTokenization: function() {
        return new Promise((resolve, reject) => {
            console.log('Pagar.me: Starting card tokenization...');
            
            // Validate that all form fields are filled
            if (!this._validateFormFields()) {
                reject(new Error('Dados do cartão incompletos'));
                return;
            }

            // Check if Pagar.me tokenizecard.js is loaded
            if (typeof window.PagarMeTokenize === 'undefined') {
                console.error('Pagar.me: tokenizecard.js not loaded');
                reject(new Error('Biblioteca de tokenização não carregada'));
                return;
            }

            try {
                // Get card data directly from form fields
                const container = this._getPaymentContainer();
                if (!container) {
                    reject(new Error('Container de pagamento não encontrado'));
                    return;
                }

                const cardData = this._getCardDataFromForm(container);
                if (!cardData) {
                    reject(new Error('Falha ao obter dados do cartão'));
                    return;
                }

                // Call Pagar.me tokenization API directly
                console.log('Pagar.me: Calling tokenization API directly...');
                window.PagarMeTokenize.create(cardData).then((cardToken) => {
                    console.log('Pagar.me: Token generated successfully');
                    resolve(cardToken);
                }).catch((error) => {
                    console.error('Pagar.me: Tokenization failed:', error);
                    reject(new Error('Falha na tokenização: ' + (error.message || 'Erro desconhecido')));
                });

            } catch (error) {
                console.error('Pagar.me: Error during tokenization:', error);
                reject(error);
            }
        });
    },

    /**
     * Extract card data from form fields for direct tokenization
     * @private
     * @param {Element} container - The payment container element
     * @return {Object|null} Card data object or null if failed
     */
    _getCardDataFromForm: function(container) {
        try {
            const cardNumber = container.querySelector('[data-pagarme-checkout-element="card-number"]')?.value?.replace(/\s/g, '');
            const cardHolderName = container.querySelector('[data-pagarme-checkout-element="cardholder-name"]')?.value;
            const cardExpiryMonth = container.querySelector('[data-pagarme-checkout-element="card-expiry-month"]')?.value;
            const cardExpiryYear = container.querySelector('[data-pagarme-checkout-element="card-expiry-year"]')?.value;
            const cardCvv = container.querySelector('[data-pagarme-checkout-element="card-cvv"]')?.value;

            if (!cardNumber || !cardHolderName || !cardExpiryMonth || !cardExpiryYear || !cardCvv) {
                console.error('Pagar.me: Missing required card data');
                return null;
            }

            return {
                card_number: cardNumber,
                card_holder_name: cardHolderName,
                card_expiry_month: cardExpiryMonth,
                card_expiry_year: cardExpiryYear,
                card_cvv: cardCvv
            };
        } catch (error) {
            console.error('Pagar.me: Error extracting card data:', error);
            return null;
        }
    },

    /**
     * Validate that all required form fields are filled
     * @private
     * @return {boolean} True if all fields are valid
     */
    _validateFormFields: function() {
        const container = this._getPaymentContainer();
        if (!container) {
            console.error('Pagar.me: Payment container not found');
            return false;
        }

        // Try both data attribute selectors and direct ID selectors for compatibility
        const requiredFields = [
            { selector: 'input[data-pagarme-checkout-element="cardholder-name"], #card_holder_name', name: 'Nome do Portador' },
            { selector: 'input[data-pagarme-checkout-element="card-number"], #card_number', name: 'Número do Cartão' },
            { selector: 'select[data-pagarme-checkout-element="card-expiry-month"], #card_expiry_month', name: 'Mês de Expiração' },
            { selector: 'select[data-pagarme-checkout-element="card-expiry-year"], #card_expiry_year', name: 'Ano de Expiração' },
            { selector: 'input[data-pagarme-checkout-element="card-cvv"], #card_cvv', name: 'CVV' }
        ];

        const missingFields = [];
        for (const fieldInfo of requiredFields) {
            const field = container.querySelector(fieldInfo.selector);
            if (!field) {
                console.error('Pagar.me: Required field not found:', fieldInfo.selector);
                missingFields.push(fieldInfo.name);
            } else if (!field.value || field.value.trim() === '') {
                this._displayError('Dados Incompletos', `Campo obrigatório não preenchido: ${fieldInfo.name}`);
                return false;
            }
        }

        if (missingFields.length > 0) {
            const errorMsg = `Payment form elements not found: ${missingFields.join(', ')}`;
            console.error('Pagar.me: ' + errorMsg);
            this._displayError('Formulário de Pagamento', 'Os campos do cartão de crédito não foram encontrados. Recarregue a página.');
            return false;
        }

        return true;
    },

    /**
     * Get the payment container for the current provider
     * @private
     * @return {Element|null} The payment container element
     */
    _getPaymentContainer: function() {
        console.log('Pagar.me: Looking for payment container...');
        
        // First try to find any pagarme container
        const containers = document.querySelectorAll('[id^="pagarme-container-"]');
        console.log('Pagar.me: Found containers:', containers.length);
        
        for (let i = 0; i < containers.length; i++) {
            const container = containers[i];
            console.log(`Pagar.me: Container ${i}:`, {
                id: container.id,
                visible: container.offsetParent !== null,
                display: getComputedStyle(container).display,
                opacity: getComputedStyle(container).opacity
            });
            
            if (container.offsetParent !== null) { // Check if visible
                console.log('Pagar.me: Using visible container:', container.id);
                return container;
            }
        }
        
        // Fallback: look for any inline form element
        const inlineForm = document.querySelector('.o_payment_form .row');
        if (inlineForm) {
            console.log('Pagar.me: Using fallback inline form container');
            return inlineForm;
        }
        
        // Debug: show all payment related elements
        const allPaymentElements = document.querySelectorAll('[data-pagarme-checkout-element], .o_payment_form, .payment_option_card');
        console.log('Pagar.me: All payment-related elements found:', allPaymentElements.length);
        allPaymentElements.forEach((el, idx) => {
            console.log(`  Element ${idx}:`, el.tagName, el.className, el.id, el.getAttribute('data-pagarme-checkout-element'));
        });
        
        console.error('Pagar.me: No payment container found');
        return null;
    },

    /**
     * Prepare the inline form for Pagar.me payments.
     *
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} code - The code of the selected payment option's provider
     * @param {integer} paymentOptionId - The id of the selected payment option
     * @param {string} flow - The online payment flow of the selected payment option
     * @return {Promise}
     */
    _prepareInlineForm: function (code, paymentOptionId, flow) {
        if (code !== 'pagarme') {
            return this._super(...arguments);
        } else if (flow === 'token') {
            return Promise.resolve();
        }

        console.log('Pagar.me: Preparing inline form');
        this._setPaymentFlow('direct');
        
        // Add input formatting and ensure Pagar.me script is loaded
        setTimeout(() => {
            this._setupInputFormatting();
            this._ensurePagarmeScriptLoaded();
        }, 100);
        
        return Promise.resolve();
    },

    /**
     * Ensure Pagar.me tokenizecard.js is loaded
     * @private
     */
    _ensurePagarmeScriptLoaded: function() {
        if (typeof window.PagarMeTokenize === 'undefined') {
            console.warn('Pagar.me: tokenizecard.js not yet loaded, form tokenization may not work');
        } else {
            console.log('Pagar.me: tokenizecard.js is loaded and ready');
        }
    },

    /**
     * Setup input formatting for card fields
     * @private
     */
    _setupInputFormatting: function() {
        const container = this._getPaymentContainer();
        if (!container) {
            console.log('Pagar.me: Container not found for input formatting');
            return;
        }

        const cardNumber = container.querySelector('[data-pagarme-checkout-element="card-number"]');
        const cardCvv = container.querySelector('[data-pagarme-checkout-element="card-cvv"]');
        const cardHolder = container.querySelector('[data-pagarme-checkout-element="cardholder-name"]');

        if (cardNumber) {
            cardNumber.addEventListener('input', function() {
                const value = this.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
                const formattedValue = value.match(/.{1,4}/g);
                this.value = formattedValue ? formattedValue.join(' ') : '';
                if (this.value.length > 19) {
                    this.value = this.value.slice(0, 19);
                }
            });
        }

        if (cardCvv) {
            cardCvv.addEventListener('input', function() {
                this.value = this.value.replace(/[^0-9]/gi, '');
                if (this.value.length > 4) {
                    this.value = this.value.slice(0, 4);
                }
            });
        }

        if (cardHolder) {
            cardHolder.addEventListener('input', function() {
                this.value = this.value.replace(/[^a-zA-ZÀ-ÿ\s]/gi, '');
            });
        }

        console.log('Pagar.me: Input formatting setup complete');
    },
};

checkoutForm.include(pagarmePaymentMixin);
manageForm.include(pagarmePaymentMixin);