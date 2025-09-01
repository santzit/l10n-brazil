/** @odoo-module */

import {_t} from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { debounce } from '@web/core/utils/timing';

import paymentPagarmeMixin from './payment_pagarme_mixin';

// Simple payment widget without using publicWidget to avoid website dependency
export class PaymentExpressCheckoutFormPagarme {
    constructor(element) {
        this.element = element;
        this.init();
    }

    init() {
        const submitButton = this.element.querySelector('button[name="o_payment_submit_button"]');
        if (submitButton) {
            submitButton.removeAttribute('disabled');
            submitButton.addEventListener('click', debounce(this._initiateExpressPayment.bind(this), 500, true));
        }
    }

    /**
     * Process the payment.
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _initiateExpressPayment(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        const shippingInformationRequired = document.querySelector(
            '[name="o_payment_express_checkout_form"]'
        ).dataset.shippingInfoRequired;
        const providerId = ev.target.parentElement.dataset.providerId;
        let expressDeliveryAddress = {};
        if (shippingInformationRequired){
            const shippingInfo = document.querySelector(
                `#o_payment_pagarme_shipping_info_${providerId}`
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
            // Call the shipping address update route to fetch the shipping options.
            const { delivery_methods } = await rpc(
                this.paymentContext['shippingAddressUpdateRoute'],
                {partial_delivery_address: expressDeliveryAddress},
            );
            if (delivery_methods.length > 0) {
                const id = parseInt(delivery_methods[0].id);
                await rpc('/shop/set_delivery_method', {dm_id: id});
            } else {
                alert(_t("No delivery method is available."));
                return;
            }
        }
        await rpc(
            document.querySelector(
                '[name="o_payment_express_checkout_form"]'
            ).dataset['expressCheckoutRoute'],
            {
                'shipping_address': expressDeliveryAddress,
                'billing_address': {
                    'name': 'Pagar.me User',
                    'email': 'pagarme@test.com',
                    'street': 'Rue des Bourlottes 9',
                    'street2': '23',
                    'country': 'BE',
                    'city':'Ramillies',
                    'zip':'1367'
                },
            }
        );
        const processingValues = await rpc(
            this.paymentContext['transactionRoute'],
            this._prepareTransactionRouteParams(providerId),
        )
        paymentPagarmeMixin.processPagarmePayment(processingValues);
    }

    _prepareTransactionRouteParams(providerId) {
        return {
            'provider_id': providerId,
            'payment_method_code': 'pagarme',
            'flow': 'direct',
        };
    }
}

// Initialize widgets when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const expressCheckoutForms = document.querySelectorAll('.o_payment_express_checkout_form[data-provider-code="pagarme"]');
    expressCheckoutForms.forEach(form => {
        new PaymentExpressCheckoutFormPagarme(form);
    });
});