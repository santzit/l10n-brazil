/** @odoo-module **/

import checkoutForm from 'payment.checkout_form';
import manageForm from 'payment.manage_form';

const pagarmePaymentMixin = {

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Process payment with Pagar.me using automatic tokenization via checkout.js.
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

        const self = this;
        
        // Find the payment form container and scope element search within it
        var paymentContainer = document.querySelector('[id*="pagarme-container-' + providerId + '"]') || 
                               document.querySelector('.o_payment_form') || 
                               document;

        // Get form element - Pagar.me script expects a form
        var form = paymentContainer.querySelector('form') || paymentContainer.closest('form');
        if (!form) {
            this._displayError(
                'Erro do Formulário',
                'Formulário de pagamento não encontrado. Recarregue a página e tente novamente.'
            );
            return Promise.reject(new Error('Payment form not found'));
        }

        // Get card details from the form for validation
        var cardHolderNameEl = paymentContainer.querySelector('#card_holder_name') || 
                               paymentContainer.querySelector('[name="card_holder_name"]');
        var cardNumberEl = paymentContainer.querySelector('#card_number') || 
                           paymentContainer.querySelector('[name="card_number"]');
        var cardExpiryMonthEl = paymentContainer.querySelector('#card_expiry_month') || 
                                paymentContainer.querySelector('[name="card_expiry_month"]');
        var cardExpiryYearEl = paymentContainer.querySelector('#card_expiry_year') || 
                               paymentContainer.querySelector('[name="card_expiry_year"]');
        var cardCvvEl = paymentContainer.querySelector('#card_cvv') || 
                        paymentContainer.querySelector('[name="card_cvv"]');

        // Check if all required elements exist
        if (!cardHolderNameEl || !cardNumberEl || !cardExpiryMonthEl || !cardExpiryYearEl || !cardCvvEl) {
            this._displayError(
                'Erro do Formulário',
                'Não foi possível encontrar os campos do cartão. Recarregue a página e tente novamente.'
            );
            return Promise.reject(new Error('Payment form elements not found'));
        }

        // Basic validation
        var cardHolderName = cardHolderNameEl.value;
        var cardNumber = cardNumberEl.value.replace(/\s/g, ''); // Remove spaces
        var cardExpiryMonth = cardExpiryMonthEl.value;
        var cardExpiryYear = cardExpiryYearEl.value;
        var cardCvv = cardCvvEl.value;

        if (!cardHolderName || !cardNumber || !cardExpiryMonth || !cardExpiryYear || !cardCvv) {
            this._displayError(
                'Dados Incompletos',
                'Por favor, preencha todos os campos do cartão.'
            );
            return Promise.reject(new Error('Incomplete payment data'));
        }

        // Create a temporary form submission to trigger Pagar.me tokenization
        // The Pagar.me script will automatically add "pagarmetoken" field during form submission
        return new Promise((resolve, reject) => {
            try {
                // Create a hidden form for tokenization
                var tokenForm = document.createElement('form');
                tokenForm.style.display = 'none';
                tokenForm.method = 'POST';
                
                // Copy all the card fields with data-pagarme-checkout-element attributes
                var fields = ['card_holder_name', 'card_number', 'card_expiry_month', 'card_expiry_year', 'card_cvv'];
                fields.forEach(function(fieldName) {
                    var originalField = paymentContainer.querySelector('[name="' + fieldName + '"]');
                    if (originalField) {
                        var clonedField = originalField.cloneNode(true);
                        tokenForm.appendChild(clonedField);
                    }
                });

                document.body.appendChild(tokenForm);

                // Override form submission to capture the token
                var originalSubmit = tokenForm.submit;
                tokenForm.submit = function() {
                    // At this point, Pagar.me should have added the pagarmetoken field
                    var tokenField = tokenForm.querySelector('[name="pagarmetoken"]');
                    if (tokenField && tokenField.value) {
                        var cardToken = tokenField.value;
                        console.log('Pagar.me: Card tokenized successfully');
                        
                        // Clean up the temporary form
                        document.body.removeChild(tokenForm);
                        
                        // Send tokenized data to server
                        self._rpc({
                            route: '/payment/pagarme/payment',
                            params: {
                                'reference': processingValues.reference,
                                'card_token': cardToken,
                                'card_holder_name': cardHolderName,
                                'amount': processingValues.amount,
                                'currency': processingValues.currency,
                            },
                        }).then((result) => {
                            if (result.error) {
                                self._displayError(
                                    'Erro no Pagamento',
                                    result.error
                                );
                                reject(new Error(result.error));
                            } else {
                                console.log('Pagar.me: Payment processed successfully');
                                window.location = '/payment/status';
                                resolve(result);
                            }
                        }).catch((error) => {
                            console.error('Pagar.me: Payment request failed:', error);
                            self._displayError(
                                'Erro no Pagamento',
                                'Ocorreu um erro ao processar o pagamento. Tente novamente.'
                            );
                            reject(error);
                        });
                    } else {
                        // Clean up and show error
                        document.body.removeChild(tokenForm);
                        self._displayError(
                            'Erro na Tokenização',
                            'Não foi possível gerar o token do cartão. Verifique as informações e tente novamente.'
                        );
                        reject(new Error('Token not generated'));
                    }
                };

                // Add a small delay to ensure Pagar.me script is ready, then submit
                setTimeout(function() {
                    tokenForm.submit();
                }, 100);

            } catch (error) {
                console.error('Pagar.me: Tokenization setup failed:', error);
                self._displayError(
                    'Erro na Tokenização',
                    'Não foi possível configurar a tokenização. Recarregue a página e tente novamente.'
                );
                reject(error);
            }
        });
    },

    /**
     * Prepare the inline form of Pagar.me for direct payment.
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

        // Set the payment flow to direct payment (inline processing)
        this._setPaymentFlow('direct');
        
        // Add input formatting for card number with scoped search
        var paymentContainer = document.querySelector('[id*="pagarme-container-' + paymentOptionId + '"]') || 
                               document.querySelector('.o_payment_form') || 
                               document;
                               
        var cardNumberInput = paymentContainer.querySelector('#card_number') || 
                              paymentContainer.querySelector('[name="card_number"]');
                              
        if (cardNumberInput) {
            cardNumberInput.addEventListener('input', function() {
                var value = this.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
                var formattedValue = value.match(/.{1,4}/g);
                this.value = formattedValue ? formattedValue.join(' ') : '';
                
                // Limit to 19 characters (16 digits + 3 spaces)
                if (this.value.length > 19) {
                    this.value = this.value.slice(0, 19);
                }
            });
        }

        // Add CVV input validation
        var cardCvvInput = paymentContainer.querySelector('#card_cvv') || 
                           paymentContainer.querySelector('[name="card_cvv"]');
        if (cardCvvInput) {
            cardCvvInput.addEventListener('input', function() {
                this.value = this.value.replace(/[^0-9]/gi, '');
                if (this.value.length > 4) {
                    this.value = this.value.slice(0, 4);
                }
            });
        }

        // Add cardholder name validation
        var cardHolderInput = paymentContainer.querySelector('#card_holder_name') || 
                              paymentContainer.querySelector('[name="card_holder_name"]');
        if (cardHolderInput) {
            cardHolderInput.addEventListener('input', function() {
                // Allow letters, spaces, and common name characters
                this.value = this.value.replace(/[^a-zA-ZÀ-ÿ\s]/gi, '');
            });
        }

        return Promise.resolve();
    },
};

checkoutForm.include(pagarmePaymentMixin);
manageForm.include(pagarmePaymentMixin);