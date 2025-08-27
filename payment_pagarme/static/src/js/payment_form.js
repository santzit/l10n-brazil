/** @odoo-module **/

import checkoutForm from 'payment.checkout_form';

// Add Pagar.me functionality to the checkout form for redirect payment
checkoutForm.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Redirect to Pagar.me checkout for redirect payment flow.
     * This removes the complex direct payment implementation that was causing errors.
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
        
        // Get checkout URL from processing values
        const checkoutUrl = processingValues.checkout_url;
        if (!checkoutUrl) {
            console.error('❌ Pagar.me: Missing checkout URL');
            this._displayError(
                "Configuration Error",
                "Unable to redirect to Pagar.me checkout",
                "Missing checkout URL"
            );
            return Promise.reject(new Error('Missing checkout URL'));
        }
        
        console.log('🚀 Pagar.me: Redirecting to checkout:', checkoutUrl);
        
        // Redirect to Pagar.me checkout
        window.location.assign(checkoutUrl);
        
        // Return a resolved promise since we're redirecting
        return Promise.resolve();
    },

    /**
     * Prepare the inline form for Pagar.me provider (simplified for redirect flow)
     *
     * @override
     * @private
     * @param {string} providerCode - The provider code
     * @param {number} providerId - The provider id
     * @param {string} flowType - The payment flow type
     * @return {Promise}
     */
    _prepareInlineForm: function (providerCode, providerId, flowType) {
        if (providerCode !== 'pagarme') {
            return this._super(...arguments);
        }

        console.log('🚀 Pagar.me: Preparing redirect form for provider', providerId);
        
        // For redirect payment, no complex form preparation needed
        // Just ensure the redirect button/form is ready
        return Promise.resolve();
    },

});

console.log('✅ Pagar.me redirect payment module loaded successfully!');