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
        
        // Wait for DOM to be fully loaded and form elements to be available
        return new Promise((resolve, reject) => {
            const maxAttempts = 50; // 5 seconds total (50 * 100ms)
            let attempts = 0;
            
            function tryFindElements() {
                attempts++;
                
                // Try multiple strategies to find the payment container
                var paymentContainer = null;
                
                // Strategy 1: Look for specific Pagar.me container
                var containers = document.querySelectorAll('[id*="pagarme-container"]');
                if (containers.length > 0) {
                    paymentContainer = containers[0];
                }
                
                // Strategy 2: Look for any payment form
                if (!paymentContainer) {
                    paymentContainer = document.querySelector('.o_payment_form');
                }
                
                // Strategy 3: Look for form containing our specific fields
                if (!paymentContainer) {
                    var holderInput = document.querySelector('input[name="card_holder_name"], #card_holder_name');
                    if (holderInput) {
                        paymentContainer = holderInput.closest('form') || holderInput.closest('.o_payment_form') || document;
                    }
                }
                
                // Strategy 4: Use document as fallback
                if (!paymentContainer) {
                    paymentContainer = document;
                }

                console.log('Pagar.me: Payment container found:', paymentContainer);
                console.log('Pagar.me: Provider ID:', providerId);
                console.log('Pagar.me: Attempt:', attempts);

                // Try to find all required form elements using multiple selectors
                function findElement(selectors) {
                    for (let selector of selectors) {
                        let element = paymentContainer.querySelector(selector) || document.querySelector(selector);
                        if (element) return element;
                    }
                    return null;
                }

                var cardHolderNameEl = findElement([
                    'input[name="card_holder_name"]',
                    '#card_holder_name',
                    'input[placeholder*="Nome"]',
                    'input[data-pagarme-checkout-element="cardholder-name"]'
                ]);
                
                var cardNumberEl = findElement([
                    'input[name="card_number"]',
                    '#card_number',
                    'input[placeholder*="1234"]',
                    'input[data-pagarme-checkout-element="card-number"]'
                ]);
                
                var cardExpiryMonthEl = findElement([
                    'select[name="card_expiry_month"]',
                    '#card_expiry_month',
                    'select[data-pagarme-checkout-element="card-expiry-month"]'
                ]);
                
                var cardExpiryYearEl = findElement([
                    'select[name="card_expiry_year"]',
                    '#card_expiry_year',
                    'select[data-pagarme-checkout-element="card-expiry-year"]'
                ]);
                
                var cardCvvEl = findElement([
                    'input[name="card_cvv"]',
                    '#card_cvv',
                    'input[placeholder*="123"]',
                    'input[data-pagarme-checkout-element="card-cvv"]'
                ]);

                // Debug log to help diagnose issues
                console.log('Pagar.me: Form elements found:', {
                    cardHolderName: !!cardHolderNameEl,
                    cardNumber: !!cardNumberEl,
                    expiryMonth: !!cardExpiryMonthEl,
                    expiryYear: !!cardExpiryYearEl,
                    cvv: !!cardCvvEl
                });

                // Check if all required elements exist
                if (cardHolderNameEl && cardNumberEl && cardExpiryMonthEl && cardExpiryYearEl && cardCvvEl) {
                    // All elements found, proceed with payment processing
                    console.log('Pagar.me: All form elements found successfully');
                    self._processPagarmePayment(
                        cardHolderNameEl, cardNumberEl, cardExpiryMonthEl, 
                        cardExpiryYearEl, cardCvvEl, processingValues
                    ).then(resolve).catch(reject);
                    return;
                }
                
                // If not all elements found and we haven't reached max attempts, try again
                if (attempts < maxAttempts) {
                    setTimeout(tryFindElements, 100);
                    return;
                }
                
                // Max attempts reached, show detailed error
                var missingFields = [];
                if (!cardHolderNameEl) missingFields.push('Nome do Portador');
                if (!cardNumberEl) missingFields.push('Número do Cartão');
                if (!cardExpiryMonthEl) missingFields.push('Mês de Expiração');
                if (!cardExpiryYearEl) missingFields.push('Ano de Expiração');
                if (!cardCvvEl) missingFields.push('CVV');
                
                console.error('Pagar.me: Missing form fields after', attempts, 'attempts:', missingFields);
                console.log('Pagar.me: Available form elements in container:', 
                    Array.from(paymentContainer.querySelectorAll('input, select')).map(el => ({
                        tag: el.tagName,
                        name: el.name,
                        id: el.id,
                        type: el.type,
                        placeholder: el.placeholder
                    }))
                );
                
                self._displayError(
                    'Erro do Formulário',
                    'Não foi possível encontrar os campos do cartão: ' + missingFields.join(', ') + '. Recarregue a página e tente novamente.'
                );
                reject(new Error('Payment form elements not found: ' + missingFields.join(', ')));
            }
            
            // Start the element search
            tryFindElements();
        });
    },

    /**
     * Process Pagar.me payment with found form elements
     * @private
     */
    _processPagarmePayment: function(cardHolderNameEl, cardNumberEl, cardExpiryMonthEl, cardExpiryYearEl, cardCvvEl, processingValues) {
        const self = this;

        // Get card details for validation
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

        // Find the actual form element that contains our fields
        var form = cardHolderNameEl.closest('form');
        if (!form) {
            this._displayError(
                'Erro do Formulário',
                'Formulário de pagamento não encontrado. Recarregue a página e tente novamente.'
            );
            return Promise.reject(new Error('Payment form not found'));
        }

        console.log('Pagar.me: Found payment form:', form);

        // Use Pagar.me's automatic tokenization by submitting the form
        // The Pagar.me script will intercept the submission and add the token
        return new Promise((resolve, reject) => {
            try {
                // Store the original form action and method
                var originalAction = form.action;
                var originalMethod = form.method;
                var originalTarget = form.target;
                
                // Set up a temporary submission handler
                var tokenCheckInterval;
                var attemptCount = 0;
                var maxAttempts = 50; // 5 seconds total (50 * 100ms)
                
                // Create a hidden iframe to capture the form submission
                var iframe = document.createElement('iframe');
                iframe.name = 'pagarme_token_frame';
                iframe.style.display = 'none';
                document.body.appendChild(iframe);
                
                // Set form to submit to the iframe
                form.target = 'pagarme_token_frame';
                form.action = '#';
                form.method = 'POST';
                
                // Function to check for the token
                function checkForToken() {
                    attemptCount++;
                    var tokenField = form.querySelector('input[name="pagarmetoken"]');
                    
                    if (tokenField && tokenField.value) {
                        clearInterval(tokenCheckInterval);
                        
                        var cardToken = tokenField.value;
                        console.log('Pagar.me: Card tokenized successfully');
                        
                        // Restore form properties
                        form.action = originalAction;
                        form.method = originalMethod;
                        form.target = originalTarget;
                        
                        // Clean up iframe
                        document.body.removeChild(iframe);
                        
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
                        
                    } else if (attemptCount >= maxAttempts) {
                        clearInterval(tokenCheckInterval);
                        
                        // Restore form properties
                        form.action = originalAction;
                        form.method = originalMethod;
                        form.target = originalTarget;
                        
                        // Clean up iframe
                        document.body.removeChild(iframe);
                        
                        self._displayError(
                            'Erro na Tokenização',
                            'Não foi possível gerar o token do cartão. Verifique as informações e tente novamente.'
                        );
                        reject(new Error('Token generation timeout'));
                    }
                }
                
                // Start checking for token
                tokenCheckInterval = setInterval(checkForToken, 100);
                
                // Submit the form to trigger Pagar.me tokenization
                form.submit();
                
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
        
        // Find the payment form container - try different approaches  
        var paymentContainer = document.querySelector('[id*="pagarme-container-' + paymentOptionId + '"]');
        
        if (!paymentContainer) {
            // Try to find by provider ID pattern
            var providerContainers = document.querySelectorAll('[id*="pagarme-container-"]');
            if (providerContainers.length > 0) {
                paymentContainer = providerContainers[0];
            }
        }
        
        if (!paymentContainer) {
            // Fallback to any element with o_payment_form class
            paymentContainer = document.querySelector('.o_payment_form');
        }
        
        if (!paymentContainer) {
            // Last resort - search entire document
            paymentContainer = document;
        }

        console.log('Pagar.me: Preparing inline form, container found:', paymentContainer);
        console.log('Pagar.me: Payment option ID:', paymentOptionId);
                               
        // Add input formatting for card number with scoped search
        var cardNumberInput = paymentContainer.querySelector('input[name="card_number"]') || 
                              paymentContainer.querySelector('#card_number') ||
                              document.querySelector('input[name="card_number"]');
                              
        if (cardNumberInput) {
            console.log('Pagar.me: Setting up card number formatting');
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
        var cardCvvInput = paymentContainer.querySelector('input[name="card_cvv"]') || 
                           paymentContainer.querySelector('#card_cvv') ||
                           document.querySelector('input[name="card_cvv"]');
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
        var cardHolderInput = paymentContainer.querySelector('input[name="card_holder_name"]') || 
                              paymentContainer.querySelector('#card_holder_name') ||
                              document.querySelector('input[name="card_holder_name"]');
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