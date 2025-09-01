// Use odoo framework for payment form extension
odoo.define('l10n_br_payment_pagarme.payment_form', function (require) {
    'use strict';

    var core = require('web.core');
    var PaymentForm = require('payment.payment_form');
    var paymentPagarmeMixin = require('l10n_br_payment_pagarme.payment_pagarme_mixin');

    PaymentForm.include({

        // #=== DOM MANIPULATION ===#

        /**
         * Prepare the inline form of Pagar.me for direct payment.
         *
         * @override method from payment.payment_form
         * @private
         * @param {number} providerId - The id of the selected payment option's provider.
         * @param {string} providerCode - The code of the selected payment option's provider.
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} paymentMethodCode - The code of the selected payment method, if any.
         * @param {string} flow - The online payment flow of the selected payment option.
         * @return {void}
         */
        _prepareInlineForm: function (providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
            if (providerCode !== 'pagarme') {
                this._super.apply(this, arguments);
                return;
            } else if (flow === 'token') {
                return;
            }
            this._setPaymentFlow('direct');
        },

        // #=== PAYMENT FLOW ===#

        /**
         * Simulate a feedback from a payment provider and redirect the customer to the status page.
         *
         * @override method from payment.payment_form
         * @private
         * @param {string} providerCode - The code of the selected payment option's provider.
         * @param {number} paymentOptionId - The id of the selected payment option.
         * @param {string} paymentMethodCode - The code of the selected payment method, if any.
         * @param {object} processingValues - The processing values of the transaction.
         * @return {void}
         */
        _processDirectFlow: function (providerCode, paymentOptionId, paymentMethodCode, processingValues) {
            if (providerCode !== 'pagarme') {
                this._super.apply(this, arguments);
                return;
            }
            paymentPagarmeMixin.processPagarmePayment(processingValues);
        },

    });

    return PaymentForm;
});