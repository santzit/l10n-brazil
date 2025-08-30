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
                // Trigger form submission to let Pagar.me handle tokenization
                // Pagar.me will automatically add 'pagarmetoken' field to the form
                const container = this._getPaymentContainer();
                if (!container) {
                    reject(new Error('Container de pagamento não encontrado'));
                    return;
                }

                // Create a temporary form to trigger Pagar.me tokenization
                const tempForm = document.createElement('form');
                tempForm.style.display = 'none';
                
                // Copy all card input fields to temp form
                const cardFields = container.querySelectorAll('[data-pagarme-checkout-element]');
                cardFields.forEach(field => {
                    const clone = field.cloneNode(true);
                    tempForm.appendChild(clone);
                });

                document.body.appendChild(tempForm);

                // Listen for pagarmetoken creation
                const checkForToken = () => {
                    const tokenField = tempForm.querySelector('input[name="pagarmetoken"]');
                    if (tokenField && tokenField.value) {
                        console.log('Pagar.me: Token generated successfully');
                        const token = tokenField.value;
                        document.body.removeChild(tempForm);
                        resolve(token);
                    } else {
                        // Check again after a short delay
                        setTimeout(checkForToken, 100);
                    }
                };

                // Submit the form to trigger Pagar.me tokenization
                const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
                tempForm.dispatchEvent(submitEvent);
                
                // Start checking for the token
                setTimeout(checkForToken, 100);
                
                // Timeout after 10 seconds
                setTimeout(() => {
                    if (document.body.contains(tempForm)) {
                        document.body.removeChild(tempForm);
                        reject(new Error('Timeout na tokenização'));
                    }
                }, 10000);

            } catch (error) {
                console.error('Pagar.me: Error during tokenization:', error);
                reject(error);
            }
        });
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

        const requiredFields = [
            'input[data-pagarme-checkout-element="cardholder-name"]',
            'input[data-pagarme-checkout-element="card-number"]', 
            'select[data-pagarme-checkout-element="card-expiry-month"]',
            'select[data-pagarme-checkout-element="card-expiry-year"]',
            'input[data-pagarme-checkout-element="card-cvv"]'
        ];

        for (const selector of requiredFields) {
            const field = container.querySelector(selector);
            if (!field) {
                console.error('Pagar.me: Required field not found:', selector);
                return false;
            }
            if (!field.value || field.value.trim() === '') {
                const fieldName = field.getAttribute('data-pagarme-checkout-element');
                this._displayError('Dados Incompletos', `Campo obrigatório não preenchido: ${fieldName}`);
                return false;
            }
        }

        return true;
    },

    /**
     * Get the payment container for the current provider
     * @private
     * @return {Element|null} The payment container element
     */
    _getPaymentContainer: function() {
        // Look for the pagarme container that should be visible
        const containers = document.querySelectorAll('[id^="pagarme-container-"]');
        for (const container of containers) {
            if (container.offsetParent !== null) { // Check if visible
                return container;
            }
        }
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