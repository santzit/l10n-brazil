/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { loadJS } from "@web/core/assets";
import checkoutForm from "payment.checkout_form";
import manageForm from "payment.manage_form";

const stonePagarmePaymentForm = {

    /**
     * Initialize Stone/Pagar.me payment form
     */
    init: function() {
        this._super.apply(this, arguments);
        this.stonePagarmeLoaded = false;
    },

    /**
     * Load Stone/Pagar.me SDK
     */
    async _loadStonePagarmeSDK() {
        if (this.stonePagarmeLoaded) {
            return Promise.resolve();
        }
        
        // Load Stone/Pagar.me checkout SDK
        await loadJS('https://assets.pagar.me/checkout/1.1.0/js/checkout.js');
        this.stonePagarmeLoaded = true;
        
        return Promise.resolve();
    },

    /**
     * Prepare Stone/Pagar.me payment form
     */
    async _prepareInlineForm(providerCode, paymentMethodCode, checkedRadio) {
        if (providerCode !== 'stone_pagarme') {
            return this._super(...arguments);
        }

        // Load Stone/Pagar.me SDK
        await this._loadStonePagarmeSDK();

        // Show inline form
        this._showInlineForm(providerCode, paymentMethodCode, checkedRadio);
    },

    /**
     * Show Stone/Pagar.me inline form
     */
    _showInlineForm(providerCode, paymentMethodCode, checkedRadio) {
        const inlineForm = this._getInlineForm(providerCode, paymentMethodCode);
        inlineForm.removeClass('d-none');

        // Initialize form validation
        this._initializeFormValidation(inlineForm);
    },

    /**
     * Initialize form validation
     */
    _initializeFormValidation(inlineForm) {
        const cardNumberInput = inlineForm.find('input[name="card_number"]');
        const expiryInput = inlineForm.find('input[name="card_expiration_date"]');
        const cvvInput = inlineForm.find('input[name="card_cvv"]');

        // Format card number
        cardNumberInput.on('input', function() {
            let value = this.value.replace(/\D/g, '');
            value = value.replace(/(\d{4})(?=\d)/g, '$1 ');
            this.value = value;
        });

        // Format expiry date  
        expiryInput.on('input', function() {
            let value = this.value.replace(/\D/g, '');
            if (value.length >= 2) {
                value = value.substring(0, 2) + '/' + value.substring(2, 4);
            }
            this.value = value;
        });

        // Limit CVV to 4 digits
        cvvInput.on('input', function() {
            this.value = this.value.replace(/\D/g, '').substring(0, 4);
        });
    },

    /**
     * Process Stone/Pagar.me payment
     */
    async _processDirectPayment(providerCode, paymentMethodCode, processingValues) {
        if (providerCode !== 'stone_pagarme') {
            return this._super(...arguments);
        }

        const inlineForm = this._getInlineForm(providerCode, paymentMethodCode);
        const formData = this._getStonePagarmeFormData(inlineForm);

        // Validate form data
        if (!this._validateStonePagarmeFormData(formData)) {
            return Promise.reject();
        }

        // Show processing state
        this._showProcessingState(inlineForm);

        try {
            // Make payment request
            const result = await this._makeStonePagarmePaymentRequest(formData, processingValues);
            
            if (result.status === 'success') {
                window.location.href = result.redirect_url;
            } else {
                this._showError(inlineForm, result.message || _t('Payment processing failed'));
                this._hideProcessingState(inlineForm);
            }
        } catch (error) {
            this._showError(inlineForm, _t('Payment processing failed. Please try again.'));
            this._hideProcessingState(inlineForm);
        }
    },

    /**
     * Get form data from Stone/Pagar.me form
     */
    _getStonePagarmeFormData(inlineForm) {
        return {
            card_number: inlineForm.find('input[name="card_number"]').val().replace(/\s/g, ''),
            card_holder_name: inlineForm.find('input[name="card_holder_name"]').val(),
            card_expiration_date: inlineForm.find('input[name="card_expiration_date"]').val(),
            card_cvv: inlineForm.find('input[name="card_cvv"]').val(),
            installments: inlineForm.find('select[name="installments"]').val() || 1,
            reference: this.$el.find('input[name="reference"]').val(),
        };
    },

    /**
     * Validate Stone/Pagar.me form data
     */
    _validateStonePagarmeFormData(formData) {
        const errors = [];

        if (!formData.card_number || formData.card_number.length < 13) {
            errors.push(_t('Invalid card number'));
        }

        if (!formData.card_holder_name) {
            errors.push(_t('Card holder name is required'));
        }

        if (!formData.card_expiration_date || !/^\d{2}\/\d{2}$/.test(formData.card_expiration_date)) {
            errors.push(_t('Invalid expiration date'));
        }

        if (!formData.card_cvv || formData.card_cvv.length < 3) {
            errors.push(_t('Invalid CVV'));
        }

        if (errors.length > 0) {
            this._showError(this._getInlineForm('stone_pagarme'), errors.join(', '));
            return false;
        }

        return true;
    },

    /**
     * Make payment request to Stone/Pagar.me
     */
    async _makeStonePagarmePaymentRequest(formData, processingValues) {
        const response = await fetch('/payment/stone_pagarme/process_payment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify(formData),
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        return await response.json();
    },

    /**
     * Show processing state
     */
    _showProcessingState(inlineForm) {
        inlineForm.find('.payment-form').hide();
        inlineForm.find('.payment-processing').show();
        this.$el.find('button[name="o_payment_submit_button"]').prop('disabled', true);
    },

    /**
     * Hide processing state
     */
    _hideProcessingState(inlineForm) {
        inlineForm.find('.payment-form').show();
        inlineForm.find('.payment-processing').hide();
        this.$el.find('button[name="o_payment_submit_button"]').prop('disabled', false);
    },

    /**
     * Show error message
     */
    _showError(inlineForm, message) {
        const alertDiv = $('<div class="alert alert-danger" role="alert"></div>').text(message);
        inlineForm.find('.stone_pagarme_errors').empty().append(alertDiv);
    },

    /**
     * Clear error messages
     */
    _clearErrors(inlineForm) {
        inlineForm.find('.stone_pagarme_errors').empty();
    },

};

// Apply to checkout form
checkoutForm.include(stonePagarmePaymentForm);

// Apply to manage form  
manageForm.include(stonePagarmePaymentForm);