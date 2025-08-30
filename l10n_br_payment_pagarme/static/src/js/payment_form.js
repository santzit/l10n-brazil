/** @odoo-module **/

import checkoutForm from 'payment.checkout_form';
import manageForm from 'payment.manage_form';

const pagarmePaymentMixin = {

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Process payment with Pagar.me using tokenization.
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
        
        console.log('Pagar.me: Starting payment processing for provider ID:', providerId);
        console.log('Pagar.me: Processing values:', processingValues);
        
        return new Promise((resolve, reject) => {
            // Simple direct element lookup using IDs
            const elements = {
                cardHolderName: document.getElementById('pagarme_card_holder_name'),
                cardNumber: document.getElementById('pagarme_card_number'),
                cardExpiryMonth: document.getElementById('pagarme_card_expiry_month'),
                cardExpiryYear: document.getElementById('pagarme_card_expiry_year'),
                cardCvv: document.getElementById('pagarme_card_cvv')
            };
            
            // Check if all elements are found
            const missingElements = Object.keys(elements).filter(key => !elements[key]);
            
            if (missingElements.length > 0) {
                console.error('Pagar.me: Missing form elements:', missingElements);
                self._displayError(
                    'Erro do Formulário',
                    'Campos do cartão não encontrados. Recarregue a página e tente novamente.'
                );
                reject(new Error('Payment form elements not found: ' + missingElements.join(', ')));
                return;
            }
            
            console.log('Pagar.me: All form elements found, processing payment...');
            this.processPaymentWithElements(elements, processingValues, resolve, reject);
        });
    },
    
    /**
     * Process payment once all form elements are found
     * @private
     */
    processPaymentWithElements: function(elements, processingValues, resolve, reject) {
        const self = this;
        
        // Validate card data
        const cardHolderName = elements.cardHolderName.value.trim();
        const cardNumber = elements.cardNumber.value.replace(/\s/g, '');
        const cardExpiryMonth = elements.cardExpiryMonth.value;
        const cardExpiryYear = elements.cardExpiryYear.value;
        const cardCvv = elements.cardCvv.value;

        if (!cardHolderName || !cardNumber || !cardExpiryMonth || !cardExpiryYear || !cardCvv) {
            self._displayError(
                'Dados Incompletos',
                'Por favor, preencha todos os campos do cartão.'
            );
            reject(new Error('Incomplete payment data'));
            return;
        }

        console.log('Pagar.me: Form data validated, processing tokenization...');

        // Create a temporary form for Pagar.me tokenization if none exists
        let form = document.createElement('form');
        form.method = 'POST';
        form.action = '#';
        form.style.display = 'none';
        
        // Clone the form elements and add to form for tokenization
        Object.entries(elements).forEach(([key, element]) => {
            const clone = element.cloneNode(true);
            form.appendChild(clone);
        });
        
        document.body.appendChild(form);

        // Submit the form to trigger Pagar.me tokenization
        try {
            console.log('Pagar.me: Submitting form for tokenization...');
            
            // Check if Pagar.me tokenization library is loaded
            if (typeof window.PagarmeJS === 'undefined') {
                console.warn('Pagar.me: Tokenization library not loaded, proceeding with direct processing');
                
                // Fallback: send card data directly to server (will be tokenized there)
                self._rpc({
                    route: '/payment/pagarme/payment',
                    params: {
                        'reference': processingValues.reference,
                        'card_holder_name': cardHolderName,
                        'card_number': cardNumber,
                        'card_expiry_month': cardExpiryMonth,
                        'card_expiry_year': cardExpiryYear,
                        'card_cvv': cardCvv,
                        'amount': processingValues.amount,
                        'currency': processingValues.currency,
                    },
                }).then((result) => {
                    if (result.error) {
                        self._displayError('Erro no Pagamento', result.error);
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
                
                return;
            }
            
            // If library is loaded, use tokenization
            form.submit();
            
            // Wait for tokenization to complete
            const maxAttempts = 50; // 5 seconds total
            let attempts = 0;
            
            const checkForToken = () => {
                attempts++;
                const tokenField = form.querySelector('input[name="pagarmetoken"]');
                
                if (tokenField && tokenField.value) {
                    const cardToken = tokenField.value;
                    console.log('Pagar.me: Card tokenized successfully');
                    
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
                            self._displayError('Erro no Pagamento', result.error);
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
                    
                } else if (attempts >= maxAttempts) {
                    self._displayError(
                        'Erro na Tokenização',
                        'Não foi possível gerar o token do cartão. Verifique as informações e tente novamente.'
                    );
                    reject(new Error('Token generation timeout'));
                } else {
                    setTimeout(checkForToken, 100);
                }
            };
            
            // Start checking for token
            setTimeout(checkForToken, 100);
            
        } catch (error) {
            console.error('Pagar.me: Tokenization setup failed:', error);
            self._displayError(
                'Erro na Tokenização',
                'Não foi possível configurar a tokenização. Recarregue a página e tente novamente.'
            );
            reject(error);
        } finally {
            // Clean up temporary form
            if (form && form.parentNode) {
                form.parentNode.removeChild(form);
            }
        }
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
        
        console.log('Pagar.me: Preparing inline form for payment option:', paymentOptionId);
        console.log('Pagar.me: Payment flow set to:', flow);
        
        return new Promise((resolve) => {
            // Simple setup for form inputs
            const cardNumberInput = document.getElementById('pagarme_card_number');
            const cardCvvInput = document.getElementById('pagarme_card_cvv');
            const cardHolderInput = document.getElementById('pagarme_card_holder_name');
            
            if (cardNumberInput) {
                console.log('Pagar.me: Setting up card number formatting');
                cardNumberInput.addEventListener('input', function() {
                    const value = this.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
                    const formattedValue = value.match(/.{1,4}/g);
                    this.value = formattedValue ? formattedValue.join(' ') : '';
                    
                    // Limit to 19 characters (16 digits + 3 spaces)
                    if (this.value.length > 19) {
                        this.value = this.value.slice(0, 19);
                    }
                });
            }

            if (cardCvvInput) {
                console.log('Pagar.me: Setting up CVV validation');
                cardCvvInput.addEventListener('input', function() {
                    this.value = this.value.replace(/[^0-9]/gi, '');
                    if (this.value.length > 4) {
                        this.value = this.value.slice(0, 4);
                    }
                });
            }

            if (cardHolderInput) {
                console.log('Pagar.me: Setting up cardholder name validation');
                cardHolderInput.addEventListener('input', function() {
                    // Allow letters, spaces, and common name characters
                    this.value = this.value.replace(/[^a-zA-ZÀ-ÿ\s]/gi, '');
                });
            }
            
            console.log('Pagar.me: Form preparation completed successfully');
            resolve();
        });
    },
};

checkoutForm.include(pagarmePaymentMixin);
manageForm.include(pagarmePaymentMixin);