/** @odoo-module **/

import checkoutForm from 'payment.checkout_form';
import manageForm from 'payment.manage_form';

const pagarmePaymentMixin = {

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Helper method to find an element using multiple selector strategies
     * @private
     * @param {Element|Document} container - The container to search within
     * @param {Array} selectors - Array of CSS selectors to try
     * @param {string} fieldName - Human readable field name for debugging
     * @returns {Element|null} - The found element or null
     */
    _findElement: function(container, selectors, fieldName) {
        for (const selector of selectors) {
            const element = container.querySelector(selector);
            if (element) {
                console.log(`Pagar.me: Found ${fieldName} using selector: ${selector}`);
                return element;
            }
        }
        console.log(`Pagar.me: Could not find ${fieldName} using any selector`);
        return null;
    },

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
        
        console.log('Pagar.me: Starting payment processing for provider ID:', providerId);
        console.log('Pagar.me: Processing values:', processingValues);
        
        return new Promise((resolve, reject) => {
            // Add a retry mechanism for DOM readiness
            let retryCount = 0;
            const maxRetries = 10;
            
            const attemptProcessPayment = () => {
                console.log(`Pagar.me: DOM search attempt ${retryCount + 1}/${maxRetries}`);
                
                // Try multiple search strategies - start simple, get more complex
                const searchStrategies = [
                    // Strategy 1: Direct ID search in document
                    () => ({
                        cardHolderName: document.getElementById('pagarme_card_holder_name'),
                        cardNumber: document.getElementById('pagarme_card_number'),
                        cardExpiryMonth: document.getElementById('pagarme_card_expiry_month'),
                        cardExpiryYear: document.getElementById('pagarme_card_expiry_year'),
                        cardCvv: document.getElementById('pagarme_card_cvv')
                    }),
                    
                    // Strategy 2: Search by name attributes
                    () => ({
                        cardHolderName: document.querySelector('input[name="pagarme_card_holder_name"]'),
                        cardNumber: document.querySelector('input[name="pagarme_card_number"]'),
                        cardExpiryMonth: document.querySelector('select[name="pagarme_card_expiry_month"]'),
                        cardExpiryYear: document.querySelector('select[name="pagarme_card_expiry_year"]'),
                        cardCvv: document.querySelector('input[name="pagarme_card_cvv"]')
                    }),
                    
                    // Strategy 3: Search by data attributes
                    () => ({
                        cardHolderName: document.querySelector('[data-pagarme-checkout-element="cardholder-name"]'),
                        cardNumber: document.querySelector('[data-pagarme-checkout-element="card-number"]'),
                        cardExpiryMonth: document.querySelector('[data-pagarme-checkout-element="card-expiry-month"]'),
                        cardExpiryYear: document.querySelector('[data-pagarme-checkout-element="card-expiry-year"]'),
                        cardCvv: document.querySelector('[data-pagarme-checkout-element="card-cvv"]')
                    })
                ];
                
                let elements = null;
                
                // Try each strategy until we find all elements
                for (let i = 0; i < searchStrategies.length; i++) {
                    elements = searchStrategies[i]();
                    
                    // Check if we found all required elements
                    if (elements.cardHolderName && elements.cardNumber && 
                        elements.cardExpiryMonth && elements.cardExpiryYear && elements.cardCvv) {
                        console.log(`Pagar.me: Found all elements using strategy ${i + 1}`);
                        break;
                    } else {
                        elements = null;
                    }
                }
                
                // If we found all elements, proceed with payment
                if (elements) {
                    console.log('Pagar.me: All required form elements found');
                    this.processPaymentWithElements(elements, processingValues, resolve, reject);
                    return;
                }
                
                // Log debug information about what's in the DOM
                console.log('Pagar.me: Form elements not found. Debug info:');
                console.log('Forms:', Array.from(document.querySelectorAll('form')).map(f => ({
                    id: f.id, 
                    className: f.className,
                    hasClass: f.classList.contains('o_payment_form_pagarme')
                })));
                console.log('Pagarme elements:', Array.from(document.querySelectorAll('[data-pagarme-checkout-element]')));
                console.log('All inputs:', Array.from(document.querySelectorAll('input')).map(i => ({
                    id: i.id, 
                    name: i.name, 
                    type: i.type
                })));
                
                // Retry if we haven't reached max attempts
                if (retryCount < maxRetries) {
                    retryCount++;
                    setTimeout(attemptProcessPayment, 200);
                } else {
                    console.error('Pagar.me: Could not find payment form elements after all attempts');
                    const missingFields = ['Nome do Portador', 'Número do Cartão', 'Mês de Expiração', 'Ano de Expiração', 'CVV'];
                    self._displayError(
                        'Erro do Formulário',
                        'Não foi possível encontrar os campos do cartão. Por favor, recarregue a página e tente novamente.'
                    );
                    reject(new Error('Payment form elements not found: ' + missingFields.join(', ')));
                }
            };
            
            // Start the search process
            attemptProcessPayment.call(this);
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

        // Find or create form for Pagar.me tokenization
        let form = elements.cardHolderName.closest('form');
        
        if (!form) {
            console.log('Pagar.me: No form found, using existing form structure');
            form = document.querySelector('.o_payment_form_pagarme');
            
            if (!form) {
                console.log('Pagar.me: Creating temporary form for tokenization');
                form = document.createElement('form');
                form.className = 'o_payment_form_pagarme';
                form.method = 'POST';
                form.action = '#';
                form.style.display = 'none';
                
                // Clone the existing elements into the form
                Object.values(elements).forEach(element => {
                    const clone = element.cloneNode(true);
                    form.appendChild(clone);
                });
                
                document.body.appendChild(form);
            }
        }

        // Use Pagar.me's automatic tokenization
        try {
            console.log('Pagar.me: Submitting form for tokenization...');
            
            // Submit the form to trigger Pagar.me tokenization
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
        
        // Simple setup - wait for DOM to be ready then add input formatting
        setTimeout(() => {
            // Add input formatting for card number
            const cardNumberInput = document.getElementById('pagarme_card_number') ||
                                   document.querySelector('input[name="pagarme_card_number"]');
            
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
            const cardCvvInput = document.getElementById('pagarme_card_cvv') ||
                                document.querySelector('input[name="pagarme_card_cvv"]');
            
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
            const cardHolderInput = document.getElementById('pagarme_card_holder_name') ||
                                   document.querySelector('input[name="pagarme_card_holder_name"]');
            
            if (cardHolderInput) {
                console.log('Pagar.me: Setting up cardholder name validation');
                cardHolderInput.addEventListener('input', function() {
                    // Allow letters, spaces, and common name characters
                    this.value = this.value.replace(/[^a-zA-ZÀ-ÿ\s]/gi, '');
                });
            }
        }, 100);

        return Promise.resolve();
    },
};

checkoutForm.include(pagarmePaymentMixin);
manageForm.include(pagarmePaymentMixin);