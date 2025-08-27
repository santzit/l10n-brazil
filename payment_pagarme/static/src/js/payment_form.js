/** @odoo-module **/

import { loadJS } from '@web/core/assets';
import checkoutForm from 'payment.checkout_form';
import manageForm from 'payment.manage_form';

const pagarMeMixin = {

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Handle form submission for Pagar.me payments.
     * Following Adyen pattern: get processing values then process payment.
     *
     * @private
     * @param {object} state - The form state
     * @param {object} provider - The payment provider
     * @return {Promise}
     */
    _pagarmeOnSubmit: function (state, provider) {
        console.log('🚀 Pagar.me: Processing payment submission');
        
        // Create the transaction and retrieve the processing values (following Adyen pattern)
        return this._rpc({
            route: this.txContext.transactionRoute,
            params: this._prepareTransactionRouteParams('pagarme', provider.id, 'direct'),
        }).then(processingValues => {
            console.log('✅ Pagar.me: Got processing values with reference:', processingValues.reference);
            
            // Store the reference for later use (following Adyen pattern)
            this.pagarmeReference = processingValues.reference;
            
            // Get card data from form
            const formData = this._getPagarmeFormData();
            
            // Validate form data
            if (!this._validatePagarmeForm(formData)) {
                throw new Error('Invalid form data');
            }
            
            // Initiate the payment
            return this._rpc({
                route: '/payment/pagarme/payments',
                params: {
                    'provider_id': provider.id,
                    'reference': processingValues.reference,
                    'converted_amount': processingValues.converted_amount,
                    'currency_id': processingValues.currency_id,
                    'partner_id': processingValues.partner_id,
                    'access_token': processingValues.access_token,
                    'card_data': formData,
                },
            });
        }).then(paymentResponse => {
            console.log('💳 Pagar.me: Payment response received');
            if (paymentResponse.error) {
                throw new Error(paymentResponse.error);
            }
            return paymentResponse;
        }).catch(error => {
            console.error('❌ Pagar.me: Payment error:', error);
            this._displayError(
                "Payment Error",
                "We are not able to process your payment.",
                error.message
            );
            throw error;
        });
    },

    /**
     * Get form data from Pagar.me form fields
     *
     * @private
     * @return {object} The form data
     */
    _getPagarmeFormData: function () {
        const form = this.el.querySelector('.o_pagarme_payment_form');
        if (!form) {
            throw new Error('Pagar.me form not found');
        }

        return {
            card_number: form.querySelector('#pagarme_card_number')?.value?.replace(/\s/g, '') || '',
            card_holder_name: form.querySelector('#pagarme_card_holder_name')?.value || '',
            card_exp_month: form.querySelector('#pagarme_card_exp_month')?.value || '',
            card_exp_year: form.querySelector('#pagarme_card_exp_year')?.value || '',
            card_cvv: form.querySelector('#pagarme_card_cvv')?.value || '',
            installments: form.querySelector('#pagarme_installments')?.value || '1',
        };
    },

    /**
     * Validate Pagar.me form data
     *
     * @private
     * @param {object} formData - The form data to validate
     * @return {boolean} True if valid
     */
    _validatePagarmeForm: function (formData) {
        if (!formData.card_number || formData.card_number.length < 13) {
            this._displayError("Invalid Card", "Please enter a valid card number");
            return false;
        }
        
        if (!formData.card_holder_name || formData.card_holder_name.length < 3) {
            this._displayError("Invalid Name", "Please enter the cardholder name");
            return false;
        }
        
        if (!formData.card_exp_month || !formData.card_exp_year) {
            this._displayError("Invalid Expiry", "Please enter a valid expiry date");
            return false;
        }
        
        if (!formData.card_cvv || formData.card_cvv.length < 3) {
            this._displayError("Invalid CVV", "Please enter a valid CVV");
            return false;
        }
        
        return true;
    },

    /**
     * Initialize Pagar.me form enhancements
     *
     * @private
     */
    _initializePagarmeForm: function () {
        console.log('🎯 Pagar.me: Initializing form enhancements');
        
        const form = this.el.querySelector('.o_pagarme_payment_form');
        if (!form) {
            console.warn('Pagar.me form not found, skipping initialization');
            return;
        }

        // Add input formatting
        this._setupCardNumberFormatting(form);
        this._setupExpiryFormatting(form);
        this._setupCvvFormatting(form);
        
        console.log('✅ Pagar.me: Form enhancements initialized');
    },

    /**
     * Setup card number formatting
     *
     * @private
     * @param {Element} form - The form element
     */
    _setupCardNumberFormatting: function (form) {
        const cardInput = form.querySelector('#pagarme_card_number');
        if (cardInput) {
            cardInput.addEventListener('input', function (e) {
                let value = e.target.value.replace(/\s/g, '').replace(/\D/g, '');
                value = value.replace(/(\d{4})(?=\d)/g, '$1 ');
                e.target.value = value;
            });
        }
    },

    /**
     * Setup expiry date formatting and split into month/year
     *
     * @private
     * @param {Element} form - The form element
     */
    _setupExpiryFormatting: function (form) {
        const expiryInput = form.querySelector('#pagarme_card_expiry');
        const monthInput = form.querySelector('#pagarme_card_exp_month');
        const yearInput = form.querySelector('#pagarme_card_exp_year');
        
        if (expiryInput) {
            expiryInput.addEventListener('input', function (e) {
                let value = e.target.value.replace(/\D/g, '');
                if (value.length >= 2) {
                    value = value.substring(0, 2) + '/' + value.substring(2, 4);
                }
                e.target.value = value;
                
                // Update hidden month/year fields
                const parts = value.split('/');
                if (monthInput && parts[0]) {
                    monthInput.value = parts[0];
                }
                if (yearInput && parts[1]) {
                    yearInput.value = '20' + parts[1]; // Convert YY to YYYY
                }
            });
        }
    },

    /**
     * Setup CVV formatting
     *
     * @private
     * @param {Element} form - The form element
     */
    _setupCvvFormatting: function (form) {
        const cvvInput = form.querySelector('#pagarme_card_cvv');
        if (cvvInput) {
            cvvInput.addEventListener('input', function (e) {
                e.target.value = e.target.value.replace(/\D/g, '');
            });
        }
    },
};

// Mix the Pagar.me functionality into the checkout form
checkoutForm.include({
    mixins: [pagarMeMixin],

    /**
     * Prepare the inline form for Pagar.me provider
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

        console.log('🚀 Pagar.me: Preparing inline form for provider', providerId);
        this._initializePagarmeForm();
        return Promise.resolve();
    },

    /**
     * Process the direct payment flow for Pagar.me
     *
     * @override
     * @private
     * @param {string} providerCode - The provider code
     * @param {number} providerId - The provider id
     * @param {object} processingValues - The processing values
     * @return {Promise}
     */
    _processDirectFlow: function (providerCode, providerId, processingValues) {
        if (providerCode !== 'pagarme') {
            return this._super(...arguments);
        }

        console.log('💳 Pagar.me: Processing direct payment flow');
        return this._pagarmeOnSubmit({ data: processingValues }, { id: providerId });
    },
});

// Also mix into manage form for token operations
manageForm.include({
    mixins: [pagarMeMixin],
});

console.log('✅ Pagar.me payment form module loaded successfully!');