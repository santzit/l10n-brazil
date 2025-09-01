// Simple payment widget without complex framework dependencies
odoo.define('l10n_br_payment_pagarme.express_checkout', function (require) {
    'use strict';

    var core = require('web.core');
    var paymentPagarmeMixin = require('l10n_br_payment_pagarme.payment_pagarme_mixin');
    var _t = core._t;

    var PaymentExpressCheckoutFormPagarme = core.Class.extend({
        init: function (element) {
            this.element = element;
            this._bindEvents();
        },

        _bindEvents: function () {
            var self = this;
            var submitButton = this.element.querySelector('button[name="o_payment_submit_button"]');
            if (submitButton) {
                submitButton.removeAttribute('disabled');
                submitButton.addEventListener('click', function(ev) {
                    self._initiateExpressPayment(ev);
                });
            }
        },

        /**
         * Process the payment.
         *
         * @private
         * @param {Event} ev
         * @return {void}
         */
        _initiateExpressPayment: function (ev) {
            ev.stopPropagation();
            ev.preventDefault();

            var self = this;
            var shippingInformationRequired = document.querySelector(
                '[name="o_payment_express_checkout_form"]'
            ).dataset.shippingInfoRequired;
            var providerId = ev.target.parentElement.dataset.providerId;
            var expressDeliveryAddress = {};

            if (shippingInformationRequired) {
                var shippingInfo = document.querySelector(
                    '#o_payment_pagarme_shipping_info_' + providerId
                );
                expressDeliveryAddress = {
                    'name': shippingInfo.querySelector('#o_payment_pagarme_shipping_name').value,
                    'email': shippingInfo.querySelector('#o_payment_pagarme_shipping_email').value,
                    'street': shippingInfo.querySelector('#o_payment_pagarme_shipping_address').value,
                    'street2': shippingInfo.querySelector('#o_payment_pagarme_shipping_address2').value,
                    'zip': shippingInfo.querySelector('#o_payment_pagarme_shipping_zip').value,
                    'city': shippingInfo.querySelector('#o_payment_pagarme_shipping_city').value,
                    'country': shippingInfo.querySelector('#o_payment_pagarme_shipping_country').value,
                };
            }

            // Process express checkout
            var processingValues = {
                'provider_id': providerId,
                'payment_method_code': 'pagarme',
                'flow': 'direct',
                'reference': 'EXPRESS-' + Date.now()
            };

            paymentPagarmeMixin.processPagarmePayment(processingValues);
        }
    });

    // Initialize widgets when DOM is ready
    $(document).ready(function() {
        $('.o_payment_express_checkout_form[data-provider-code="pagarme"]').each(function() {
            new PaymentExpressCheckoutFormPagarme(this);
        });
    });

    return PaymentExpressCheckoutFormPagarme;
});