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

            // Get card details from the form
            const cardHolderName = document.getElementById('card_holder_name').value;
            const cardNumber = document.getElementById('card_number').value;
            const cardExpiryMonth = document.getElementById('card_expiry_month').value;
            const cardExpiryYear = document.getElementById('card_expiry_year').value;
            const cardCvv = document.getElementById('card_cvv').value;

            // Basic validation
            if (!cardHolderName || !cardNumber || !cardExpiryMonth || !cardExpiryYear || !cardCvv) {
                this._displayError(
                    'Dados Incompletos',
                    'Por favor, preencha todos os campos do cartão.'
                );
                return Promise.reject();
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
            
            // Add input formatting for card number
            const cardNumberInput = document.getElementById('card_number');
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