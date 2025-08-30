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
        
        // First find the payment form container using the payment option ID
        const paymentOptionId = this.paymentContext?.paymentOptionId || providerId;
        let paymentContainer = null;
        
        // Try multiple strategies to find the container
        if (paymentOptionId) {
            paymentContainer = document.getElementById(`o_payment_form_pagarme_${paymentOptionId}`);
        }
        
        if (!paymentContainer) {
            paymentContainer = document.querySelector('.o_payment_form_pagarme');
        }
        
        if (!paymentContainer) {
            // Fallback: look for any container with pagarme form elements
            paymentContainer = document.querySelector('[data-pagarme-checkout-element]')?.closest('div') || document;
        }
        
        console.log('Pagar.me: Payment container found:', paymentContainer?.id || 'fallback to document');
        
        // Find payment form elements within the container scope
        const cardHolderNameEl = paymentContainer.querySelector('#card_holder_name') || 
                                paymentContainer.querySelector('input[name="card_holder_name"]') ||
                                paymentContainer.querySelector('[data-pagarme-checkout-element="cardholder-name"]');
        const cardNumberEl = paymentContainer.querySelector('#card_number') || 
                           paymentContainer.querySelector('input[name="card_number"]') ||
                           paymentContainer.querySelector('[data-pagarme-checkout-element="card-number"]');
        const cardExpiryMonthEl = paymentContainer.querySelector('#card_expiry_month') || 
                                paymentContainer.querySelector('select[name="card_expiry_month"]') ||
                                paymentContainer.querySelector('[data-pagarme-checkout-element="card-expiry-month"]');
        const cardExpiryYearEl = paymentContainer.querySelector('#card_expiry_year') || 
                               paymentContainer.querySelector('select[name="card_expiry_year"]') ||
                               paymentContainer.querySelector('[data-pagarme-checkout-element="card-expiry-year"]');
        const cardCvvEl = paymentContainer.querySelector('#card_cvv') || 
                        paymentContainer.querySelector('input[name="card_cvv"]') ||
                        paymentContainer.querySelector('[data-pagarme-checkout-element="card-cvv"]');

        // Check if all required elements exist
        const missingFields = [];
        if (!cardHolderNameEl) missingFields.push('Nome do Portador');
        if (!cardNumberEl) missingFields.push('Número do Cartão');
        if (!cardExpiryMonthEl) missingFields.push('Mês de Expiração');
        if (!cardExpiryYearEl) missingFields.push('Ano de Expiração');
        if (!cardCvvEl) missingFields.push('CVV');

        if (missingFields.length > 0) {
            console.error('Pagar.me: Missing form fields:', missingFields);
            console.log('Pagar.me: Available form elements:', 
                Array.from(document.querySelectorAll('input, select')).map(el => ({
                    tag: el.tagName,
                    name: el.name,
                    id: el.id,
                    type: el.type
                }))
            );
            
            self._displayError(
                'Erro do Formulário',
                'Não foi possível encontrar os campos do cartão: ' + missingFields.join(', ')
            );
            return Promise.reject(new Error('Payment form elements not found: ' + missingFields.join(', ')));
        }

        // Validate card data
        const cardHolderName = cardHolderNameEl.value.trim();
        const cardNumber = cardNumberEl.value.replace(/\s/g, '');
        const cardExpiryMonth = cardExpiryMonthEl.value;
        const cardExpiryYear = cardExpiryYearEl.value;
        const cardCvv = cardCvvEl.value;

        if (!cardHolderName || !cardNumber || !cardExpiryMonth || !cardExpiryYear || !cardCvv) {
            this._displayError(
                'Dados Incompletos',
                'Por favor, preencha todos os campos do cartão.'
            );
            return Promise.reject(new Error('Incomplete payment data'));
        }

        console.log('Pagar.me: All form elements found, processing payment...');

        // Find or create a form element for tokenization
        let form = cardHolderNameEl.closest('form');
        
        if (!form) {
            // Create a temporary form for Pagar.me tokenization
            form = document.createElement('form');
            form.style.display = 'none';
            form.method = 'POST';
            form.action = '#';
            
            // Add the card fields to the form
            const fields = [cardHolderNameEl, cardNumberEl, cardExpiryMonthEl, cardExpiryYearEl, cardCvvEl];
            fields.forEach(field => {
                if (field) {
                    const clone = field.cloneNode(true);
                    form.appendChild(clone);
                }
            });
            
            document.body.appendChild(form);
            console.log('Pagar.me: Created temporary form for tokenization');
        }

        // Use Pagar.me's automatic tokenization
        return new Promise((resolve, reject) => {
            try {
                // Set up event listener for token generation
                const maxAttempts = 50; // 5 seconds total
                let attempts = 0;
                
                const checkForToken = () => {
                    attempts++;
                    const tokenField = form.querySelector('input[name="pagarmetoken"]');
                    
                    if (tokenField && tokenField.value) {
                        const cardToken = tokenField.value;
                        console.log('Pagar.me: Card tokenized successfully');
                        
                        // Clean up temporary form if created
                        if (form.parentNode === document.body && form.style.display === 'none') {
                            document.body.removeChild(form);
                        }
                        
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
                        // Clean up temporary form if created
                        if (form.parentNode === document.body && form.style.display === 'none') {
                            document.body.removeChild(form);
                        }
                        
                        self._displayError(
                            'Erro na Tokenização',
                            'Não foi possível gerar o token do cartão. Verifique as informações e tente novamente.'
                        );
                        reject(new Error('Token generation timeout'));
                    } else {
                        setTimeout(checkForToken, 100);
                    }
                };
                
                // Submit the form to trigger Pagar.me tokenization
                const originalAction = form.action;
                const originalMethod = form.method;
                
                form.action = '#';
                form.method = 'POST';
                form.submit();
                
                // Start checking for token
                setTimeout(checkForToken, 100);
                
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
        
        console.log('Pagar.me: Preparing inline form for payment option:', paymentOptionId);
        
        // Find the payment form container
        const paymentContainer = document.getElementById(`o_payment_form_pagarme_${paymentOptionId}`) ||
                                document.querySelector('.o_payment_form_pagarme') ||
                                document;
        
        console.log('Pagar.me: Using container:', paymentContainer?.id || 'document');
        
        // Add input formatting for card number
        const cardNumberInput = paymentContainer.querySelector('#card_number') || 
                               paymentContainer.querySelector('input[name="card_number"]');
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

        // Add CVV input validation
        const cardCvvInput = paymentContainer.querySelector('#card_cvv') || 
                           paymentContainer.querySelector('input[name="card_cvv"]');
        if (cardCvvInput) {
            console.log('Pagar.me: Setting up CVV validation');
            cardCvvInput.addEventListener('input', function() {
                this.value = this.value.replace(/[^0-9]/gi, '');
                if (this.value.length > 4) {
                    this.value = this.value.slice(0, 4);
                }
            });
        }

        // Add cardholder name validation
        const cardHolderInput = paymentContainer.querySelector('#card_holder_name') || 
                              paymentContainer.querySelector('input[name="card_holder_name"]');
        if (cardHolderInput) {
            console.log('Pagar.me: Setting up cardholder name validation');
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