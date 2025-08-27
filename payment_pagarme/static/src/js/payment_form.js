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
        return this._super.apply(this, arguments);
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