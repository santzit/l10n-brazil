/** @odoo-module **/

import checkoutForm from 'payment.checkout_form';
import manageForm from 'payment.manage_form';

const pagarmePaymentMixin = {

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Process payment with Pagar.me using tokenization for secure handling.
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

        // Get card details from the form with defensive checks
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

        // Get values from elements
        var cardHolderName = cardHolderNameEl.value;
        var cardNumber = cardNumberEl.value.replace(/\s/g, ''); // Remove spaces
        var cardExpiryMonth = cardExpiryMonthEl.value;
        var cardExpiryYear = cardExpiryYearEl.value;
        var cardCvv = cardCvvEl.value;

        // Basic validation
        if (!cardHolderName || !cardNumber || !cardExpiryMonth || !cardExpiryYear || !cardCvv) {
            this._displayError(
                'Dados Incompletos',
                'Por favor, preencha todos os campos do cartão.'
            );
            return Promise.reject(new Error('Incomplete payment data'));
        }

        // Prepare card data object
        const cardData = {
            cardHolderName: cardHolderName,
            cardNumber: cardNumber,
            cardExpiryMonth: cardExpiryMonth,
            cardExpiryYear: cardExpiryYear,
            cardCvv: cardCvv
        };

        // Check if Tokenizacard is available, if not try to wait for it
        if (typeof window.TokenizaCard === 'undefined') {
            // Wait up to 5 seconds for the library to load
            var attempts = 0;
            var maxAttempts = 10;
            return new Promise((resolve, reject) => {
                var checkInterval = setInterval(() => {
                    attempts++;
                    if (typeof window.TokenizaCard !== 'undefined') {
                        clearInterval(checkInterval);
                        self._processPagarmePayment(processingValues, cardData).then(resolve).catch(reject);
                    } else if (attempts >= maxAttempts) {
                        clearInterval(checkInterval);
                        self._displayError(
                            'Erro de Configuração',
                            'Biblioteca de tokenização não está disponível. Isso pode ser devido a restrições de rede ou problemas de conectividade. Tente recarregar a página.'
                        );
                        reject(new Error('Tokenizacard library not available'));
                    }
                }, 500);
            });
        }

        return this._processPagarmePayment(processingValues, cardData);
    },

    /**
     * Process the actual payment with Pagar.me tokenization
     * @private
     */
    _processPagarmePayment: function(processingValues, cardData) {
        const self = this;

        // Get public key from processing values
        const publicKey = processingValues.public_key;
        if (!publicKey) {
            this._displayError(
                'Erro de Configuração',
                'Chave pública não encontrada. Verifique a configuração do provedor.'
            );
            return Promise.reject(new Error('Public key not found'));
        }

        // Initialize Tokenizacard
        const tokenizacard = new window.TokenizaCard({
            encryption_key: publicKey
        });

        // Prepare card data for tokenization
        const cardDataForToken = {
            card_number: cardData.cardNumber,
            card_holder_name: cardData.cardHolderName,
            card_expiration_date: cardData.cardExpiryMonth + cardData.cardExpiryYear.slice(-2), // MMYY format
            card_cvv: cardData.cardCvv
        };

        // Tokenize card data
        return new Promise((resolve, reject) => {
            try {
                const cardToken = tokenizacard.createCardToken(cardDataForToken);
                
                // Log tokenization success (without sensitive data)
                console.log('Pagar.me: Card tokenized successfully');
                
                // Send tokenized data to server
                self._rpc({
                    route: '/payment/pagarme/payment',
                    params: {
                        'reference': processingValues.reference,
                        'card_token': cardToken,
                        'card_holder_name': cardData.cardHolderName,
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
                
            } catch (tokenError) {
                console.error('Pagar.me: Tokenization failed:', tokenError);
                self._displayError(
                    'Erro na Tokenização',
                    'Não foi possível processar os dados do cartão. Verifique as informações e tente novamente.'
                );
                reject(tokenError);
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