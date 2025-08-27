/** @odoo-module **/

import publicWidget from 'web.public.widget';

console.log('🚀 PAGAR.ME PAYMENT FORM MODULE LOADING...');

// Simple widget for Pagar.me form enhancements (no external dependencies)
publicWidget.registry.PagarmeFormEnhancements = publicWidget.Widget.extend({
    selector: '.o_pagarme_payment_form',
    events: {
        'input #pagarme_card_number': '_onCardNumberInput',
        'input #pagarme_card_expiry': '_onExpiryInput', 
        'input #pagarme_card_cvv': '_onCvvInput',
    },

    start: function () {
        console.log('🎯 Pagar.me form enhancements initialized');
        
        // Access and log reference information for debugging
        const referenceInput = this.$('input[name="reference"]');
        if (referenceInput.length) {
            const reference = referenceInput.val();
            console.log('📝 Pagar.me: Transaction reference from form:', reference);
        }
        
        return this._super.apply(this, arguments);
    },

    /**
     * Get transaction reference for Pagar.me processing
     */
    getTransactionReference: function () {
        const referenceInput = this.$('input[name="reference"]');
        return referenceInput.length ? referenceInput.val() : null;
    },

    /**
     * Get all Pagar.me form data including reference
     */
    getPagarmeFormData: function () {
        return {
            reference: this.getTransactionReference(),
            provider_id: this.$('input[name="provider_id"]').val(),
            access_token: this.$('input[name="access_token"]').val(),
            encryption_key: this.$('input[name="encryption_key"]').val(),
        };
    },

    /**
     * Format card number input with spaces
     */
    _onCardNumberInput: function (ev) {
        const input = ev.currentTarget;
        let value = input.value.replace(/\s/g, '').replace(/\D/g, '');
        value = value.replace(/(\d{4})(?=\d)/g, '$1 ');
        input.value = value;
    },

    /**
     * Format expiry date input as MM/YY
     */
    _onExpiryInput: function (ev) {
        const input = ev.currentTarget;
        let value = input.value.replace(/\D/g, '');
        if (value.length >= 2) {
            value = value.substring(0, 2) + '/' + value.substring(2, 4);
        }
        input.value = value;
    },

    /**
     * Only allow digits in CVV
     */
    _onCvvInput: function (ev) {
        const input = ev.currentTarget;
        input.value = input.value.replace(/\D/g, '');
    },
});

console.log('✅ Pagar.me payment form module loaded successfully!');