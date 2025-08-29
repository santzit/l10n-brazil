odoo.define('l10n_br_payment_pagarme.payment_form', require => {
    'use strict';

    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');

    const pagarmePaymentMixin = {

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Process payment with Pagar.me for direct payment flow.
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

            // Find the payment form container and scope element search within it
            const paymentContainer = document.querySelector(`[id*="pagarme-container-${providerId}"]`) || 
                                   document.querySelector('.o_payment_form') || 
                                   document;

            // Get card details from the form with defensive checks
            const cardHolderNameEl = paymentContainer.querySelector('#card_holder_name') || 
                                   paymentContainer.querySelector('[name="card_holder_name"]');
            const cardNumberEl = paymentContainer.querySelector('#card_number') || 
                               paymentContainer.querySelector('[name="card_number"]');
            const cardExpiryMonthEl = paymentContainer.querySelector('#card_expiry_month') || 
                                    paymentContainer.querySelector('[name="card_expiry_month"]');
            const cardExpiryYearEl = paymentContainer.querySelector('#card_expiry_year') || 
                                   paymentContainer.querySelector('[name="card_expiry_year"]');
            const cardCvvEl = paymentContainer.querySelector('#card_cvv') || 
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
            const cardHolderName = cardHolderNameEl.value;
            const cardNumber = cardNumberEl.value;
            const cardExpiryMonth = cardExpiryMonthEl.value;
            const cardExpiryYear = cardExpiryYearEl.value;
            const cardCvv = cardCvvEl.value;

            // Basic validation
            if (!cardHolderName || !cardNumber || !cardExpiryMonth || !cardExpiryYear || !cardCvv) {
                this._displayError(
                    'Dados Incompletos',
                    'Por favor, preencha todos os campos do cartão.'
                );
                return Promise.reject(new Error('Incomplete payment data'));
            }

            // Process payment through server
            return this._rpc({
                route: '/payment/pagarme/payment',
                params: {
                    'reference': processingValues.reference,
                    'card_holder_name': cardHolderName,
                    'card_number': cardNumber.replace(/\s/g, ''), // Remove spaces
                    'card_expiry_month': cardExpiryMonth,
                    'card_expiry_year': cardExpiryYear,
                    'card_cvv': cardCvv,
                    'amount': processingValues.amount,
                    'currency': processingValues.currency,
                },
            }).then(() => {
                window.location = '/payment/status';
            }).catch((error) => {
                this._displayError(
                    'Erro no Pagamento',
                    'Ocorreu um erro ao processar o pagamento. Tente novamente.'
                );
                return Promise.reject(error);
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
            const paymentContainer = document.querySelector(`[id*="pagarme-container-${paymentOptionId}"]`) || 
                                   document.querySelector('.o_payment_form') || 
                                   document;
                                   
            const cardNumberInput = paymentContainer.querySelector('#card_number') || 
                                  paymentContainer.querySelector('[name="card_number"]');
                                  
            if (cardNumberInput) {
                cardNumberInput.addEventListener('input', function() {
                    let value = this.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
                    let formattedValue = value.match(/.{1,4}/g)?.join(' ') || '';
                    this.value = formattedValue;
                });
            }

            return Promise.resolve();
        },
    };

    checkoutForm.include(pagarmePaymentMixin);
    manageForm.include(pagarmePaymentMixin);
});