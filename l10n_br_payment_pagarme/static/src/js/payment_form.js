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
        console.log('Pagar.me: Payment context:', this.paymentContext);
        
        // Wait a bit for DOM to be fully ready
        return new Promise((resolve, reject) => {
            const processPayment = () => {
                console.log('Pagar.me: DOM ready, searching for form elements...');
                
                // Debug: List all available forms and containers
                console.log('Pagar.me: Available forms on page:', 
                    Array.from(document.querySelectorAll('form')).map(f => ({
                        id: f.id,
                        className: f.className,
                        action: f.action
                    }))
                );
                
                // Find the payment form container - use more robust detection
                const paymentOptionId = this.paymentContext?.paymentOptionId || providerId;
                let paymentContainer = null;
                
                // Strategy 1: Look for form with the exact ID pattern
                if (paymentOptionId) {
                    paymentContainer = document.getElementById(`o_payment_form_pagarme_${paymentOptionId}`);
                    if (paymentContainer) {
                        console.log('Pagar.me: Found container by ID:', paymentContainer.id);
                    }
                }
                
                // Strategy 2: Look for any form with pagarme class
                if (!paymentContainer) {
                    paymentContainer = document.querySelector('form.o_payment_form_pagarme');
                    if (paymentContainer) {
                        console.log('Pagar.me: Found container by class:', paymentContainer.className);
                    }
                }
                
                // Strategy 3: Look for any element with pagarme form elements and find its form parent
                if (!paymentContainer) {
                    const pagarmeElement = document.querySelector('[data-pagarme-checkout-element]');
                    if (pagarmeElement) {
                        paymentContainer = pagarmeElement.closest('form') || pagarmeElement.closest('.o_payment_form_pagarme') || pagarmeElement.closest('div[id*="pagarme"]');
                        if (paymentContainer) {
                            console.log('Pagar.me: Found container by pagarme element parent');
                        }
                    }
                }
                
                // Strategy 4: Look in the payment method content area
                if (!paymentContainer) {
                    paymentContainer = document.querySelector('.o_payment_method_pagarme') || 
                                      document.querySelector(`[data-payment-method-code="pagarme"]`) ||
                                      document.querySelector('.o_payment_option_card');
                    if (paymentContainer) {
                        console.log('Pagar.me: Found container by payment method area');
                    }
                }
                
                // Strategy 5: Look for the inline form element directly in any payment option
                if (!paymentContainer) {
                    const allPaymentOptions = document.querySelectorAll('.o_payment_option_card, .o_payment_option, [data-payment-option-id]');
                    for (const option of allPaymentOptions) {
                        if (option.querySelector('[data-pagarme-checkout-element]')) {
                            paymentContainer = option;
                            console.log('Pagar.me: Found container in payment option');
                            break;
                        }
                    }
                }
                
                // Fallback: use document if no specific container found
                if (!paymentContainer) {
                    console.log('Pagar.me: No specific container found, using document');
                    paymentContainer = document;
                }
                
                // Find payment form elements with extensive fallback strategies
                const cardHolderNameEl = this._findElement(paymentContainer, [
                    '#card_holder_name',
                    'input[name="card_holder_name"]',
                    '[data-pagarme-checkout-element="cardholder-name"]',
                    'input[placeholder*="nome"]',
                    'input[placeholder*="portador"]'
                ], 'Nome do Portador');
                
                const cardNumberEl = this._findElement(paymentContainer, [
                    '#card_number',
                    'input[name="card_number"]',
                    '[data-pagarme-checkout-element="card-number"]',
                    'input[placeholder*="1234"]',
                    'input[autocomplete="cc-number"]'
                ], 'Número do Cartão');
                
                const cardExpiryMonthEl = this._findElement(paymentContainer, [
                    '#card_expiry_month',
                    'select[name="card_expiry_month"]',
                    '[data-pagarme-checkout-element="card-expiry-month"]',
                    'select[autocomplete="cc-exp-month"]'
                ], 'Mês de Expiração');
                
                const cardExpiryYearEl = this._findElement(paymentContainer, [
                    '#card_expiry_year',
                    'select[name="card_expiry_year"]',
                    '[data-pagarme-checkout-element="card-expiry-year"]',
                    'select[autocomplete="cc-exp-year"]'
                ], 'Ano de Expiração');
                
                const cardCvvEl = this._findElement(paymentContainer, [
                    '#card_cvv',
                    'input[name="card_cvv"]',
                    '[data-pagarme-checkout-element="card-cvv"]',
                    'input[placeholder*="123"]',
                    'input[autocomplete="cc-csc"]'
                ], 'CVV');

                // Check if all required elements exist
                const missingFields = [];
                const foundElements = {};
                
                if (!cardHolderNameEl) {
                    missingFields.push('Nome do Portador');
                } else {
                    foundElements.cardHolderName = cardHolderNameEl;
                }
                
                if (!cardNumberEl) {
                    missingFields.push('Número do Cartão');
                } else {
                    foundElements.cardNumber = cardNumberEl;
                }
                
                if (!cardExpiryMonthEl) {
                    missingFields.push('Mês de Expiração');
                } else {
                    foundElements.cardExpiryMonth = cardExpiryMonthEl;
                }
                
                if (!cardExpiryYearEl) {
                    missingFields.push('Ano de Expiração');
                } else {
                    foundElements.cardExpiryYear = cardExpiryYearEl;
                }
                
                if (!cardCvvEl) {
                    missingFields.push('CVV');
                } else {
                    foundElements.cardCvv = cardCvvEl;
                }

                if (missingFields.length > 0) {
                    console.error('Pagar.me: Missing form fields:', missingFields);
                    console.log('Pagar.me: Container used for search:', paymentContainer);
                    console.log('Pagar.me: Found elements:', foundElements);
                    
                    // Comprehensive debugging information
                    console.log('Pagar.me: All forms on page:', 
                        Array.from(document.querySelectorAll('form')).map(f => ({
                            id: f.id,
                            className: f.className,
                            innerHTML: f.innerHTML.length + ' chars'
                        }))
                    );
                    
                    console.log('Pagar.me: All inputs on page:', 
                        Array.from(document.querySelectorAll('input, select')).map(el => ({
                            tag: el.tagName,
                            name: el.name,
                            id: el.id,
                            type: el.type,
                            className: el.className,
                            placeholder: el.placeholder
                        }))
                    );
                    
                    console.log('Pagar.me: All elements with pagarme attributes:', 
                        Array.from(document.querySelectorAll('[data-pagarme-checkout-element]')).map(el => ({
                            tag: el.tagName,
                            name: el.name,
                            id: el.id,
                            attribute: el.getAttribute('data-pagarme-checkout-element')
                        }))
                    );
                    
                    // If no elements found at all, might be timing issue - retry once
                    if (Object.keys(foundElements).length === 0) {
                        console.log('Pagar.me: No form elements found at all, retrying in 500ms...');
                        setTimeout(() => processPayment(), 500);
                        return;
                    }
                    
                    self._displayError(
                        'Erro do Formulário',
                        'Não foi possível encontrar os campos do cartão: ' + missingFields.join(', ') + 
                        '. Verifique se o formulário foi carregado corretamente.'
                    );
                    reject(new Error('Payment form elements not found: ' + missingFields.join(', ')));
                    return;
                }

                console.log('Pagar.me: All required form elements found successfully');

                // Validate card data
                const cardHolderName = cardHolderNameEl.value.trim();
                const cardNumber = cardNumberEl.value.replace(/\s/g, '');
                const cardExpiryMonth = cardExpiryMonthEl.value;
                const cardExpiryYear = cardExpiryYearEl.value;
                const cardCvv = cardCvvEl.value;

                if (!cardHolderName || !cardNumber || !cardExpiryMonth || !cardExpiryYear || !cardCvv) {
                    self._displayError(
                        'Dados Incompletos',
                        'Por favor, preencha todos os campos do cartão.'
                    );
                    reject(new Error('Incomplete payment data'));
                    return;
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
            };
            
            // Initial delay to ensure DOM is ready
            setTimeout(processPayment.bind(this), 100);
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
        
        // Find the payment form container with robust detection
        let paymentContainer = null;
        
        if (paymentOptionId) {
            paymentContainer = document.getElementById(`o_payment_form_pagarme_${paymentOptionId}`);
        }
        
        if (!paymentContainer) {
            paymentContainer = document.querySelector('form.o_payment_form_pagarme') ||
                              document.querySelector('.o_payment_form_pagarme') ||
                              document.querySelector('[data-pagarme-checkout-element]')?.closest('form') ||
                              document.querySelector('[data-pagarme-checkout-element]')?.closest('div');
        }
        
        if (!paymentContainer) {
            console.warn('Pagar.me: No payment container found, using document');
            paymentContainer = document;
        } else {
            console.log('Pagar.me: Using container:', paymentContainer.id || paymentContainer.className || 'unnamed container');
        }
        
        // Add input formatting for card number
        const cardNumberInput = this._findElement(paymentContainer, [
            '#card_number',
            'input[name="card_number"]',
            '[data-pagarme-checkout-element="card-number"]'
        ], 'Card Number Input');
        
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
        const cardCvvInput = this._findElement(paymentContainer, [
            '#card_cvv',
            'input[name="card_cvv"]',
            '[data-pagarme-checkout-element="card-cvv"]'
        ], 'CVV Input');
        
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
        const cardHolderInput = this._findElement(paymentContainer, [
            '#card_holder_name',
            'input[name="card_holder_name"]',
            '[data-pagarme-checkout-element="cardholder-name"]'
        ], 'Cardholder Name Input');
        
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