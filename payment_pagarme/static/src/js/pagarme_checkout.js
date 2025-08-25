/** @odoo-module **/

import publicWidget from 'web.public.widget';

console.log('🚀 PAGAR.ME MODULE LOADING...');

// Pagar.me payment form widget for card input handling
publicWidget.registry.PagarmePaymentForm = publicWidget.Widget.extend({
    selector: '.o_pagarme_payment_form',
    events: {
        'input #pagarme_card_number': '_onCardNumberInput',
        'input #pagarme_card_expiry': '_onExpiryInput',
        'input #pagarme_card_cvv': '_onCvvInput',
        'submit': '_onFormSubmit',
    },

    init: function () {
        this._super.apply(this, arguments);
        console.log('📦 Pagar.me payment form widget initialized');
    },

    start: function () {
        console.log('🎯 PAGAR.ME PAYMENT FORM STARTED!');
        console.log('✅ Template rendered successfully - form is ready for payment processing');
        
        // Show success message
        this._showMessage('✅ Pagar.me Ready', 'Payment form loaded successfully. Enter your card details to proceed.', 'success');
        
        return this._super.apply(this, arguments);
    },

    _onCardNumberInput: function (ev) {
        const input = ev.currentTarget;
        let value = input.value.replace(/\s/g, '').replace(/\D/g, '');
        value = value.replace(/(\d{4})(?=\d)/g, '$1 ');
        input.value = value;
    },

    _onExpiryInput: function (ev) {
        const input = ev.currentTarget;
        let value = input.value.replace(/\D/g, '');
        if (value.length >= 2) {
            value = value.substring(0, 2) + '/' + value.substring(2, 4);
        }
        input.value = value;
    },

    _onCvvInput: function (ev) {
        const input = ev.currentTarget;
        input.value = input.value.replace(/\D/g, '');
    },

    _onFormSubmit: function (ev) {
        console.log('💳 Pagar.me form submitted');
        // Form validation and processing logic would go here
        // For now, let Odoo handle the standard payment flow
    },

    _showMessage: function (title, message, type) {
        const existingMessage = document.querySelector('.pagarme-status-message');
        if (existingMessage) {
            existingMessage.remove();
        }
        
        const container = this.$el[0];
        if (!container) return;
        
        const alertClass = type === 'success' ? 'alert-success' : type === 'warning' ? 'alert-warning' : 'alert-danger';
        const icon = type === 'success' ? '✅' : type === 'warning' ? '⚠️' : '❌';
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `alert ${alertClass} pagarme-status-message`;
        messageDiv.style.cssText = 'margin: 10px 0; padding: 10px; border-radius: 5px; font-size: 14px;';
        messageDiv.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>${icon} ${title}</strong>
                    <span style="margin-left: 10px;">${message}</span>
                </div>
                <button type="button" style="background: none; border: none; font-size: 16px; cursor: pointer;" onclick="this.closest('.pagarme-status-message').remove()">&times;</button>
            </div>
        `;
        
        container.insertBefore(messageDiv, container.firstChild);
        
        // Auto-remove success messages
        if (type === 'success') {
            setTimeout(() => {
                if (messageDiv.parentElement) {
                    messageDiv.remove();
                }
            }, 10000);
        }
    },
});

console.log('🔧 Pagar.me payment form widget registered!');