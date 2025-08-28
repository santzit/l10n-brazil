/** @odoo-module **/

import checkoutForm from 'payment.checkout_form';

// Pagar.me redirect payment implementation following Adyen pattern
checkoutForm.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Redirect to Pagar.me checkout for redirect payment flow.
     * Follows Adyen pattern for redirect checkout.
     *
     * @private
     * @param {string} providerCode - The provider code
     * @param {number} providerId - The provider id
     * @param {object} processingValues - The processing values from Odoo
     * @return {Promise}
     */
    _processRedirectPayment: function (providerCode, providerId, processingValues) {
        if (providerCode !== 'pagarme') {
            return this._super(...arguments);
        }

        console.log('🔄 Pagar.me: Processing redirect payment flow');
        console.log('Processing values:', processingValues);
        
        // For redirect payment, the form should auto-submit to redirect route
        // The redirect form template handles the actual redirection
        return Promise.resolve();
    },

});

console.log('✅ Pagar.me redirect payment module loaded successfully!');