/** @odoo-module **/

import publicWidget from 'web.public.widget';

console.log('🚀 PAGAR.ME MODULE LOADING...');

// Fix for Pagar.me inline form processing
publicWidget.registry.PagarmePaymentFormFix = publicWidget.Widget.extend({
    selector: '.o_payment_form',  // Target the main payment form
    events: {
        'click button[name="o_payment_submit_button"]': '_onPayButtonClick',
    },

    init: function () {
        this._super.apply(this, arguments);
        console.log('🔧 Pagar.me payment form fix widget initialized');
    },

    start: function () {
        console.log('🎯 PAGAR.ME PAYMENT FORM FIX STARTED!');
        this._checkPagarmeProvider();
        return this._super.apply(this, arguments);
    },

    _checkPagarmeProvider: function () {
        // Check if Pagar.me provider is selected
        const pagarmeRadio = this.$el.find('input[name="provider_id"][data-provider-code="pagarme"]');
        if (pagarmeRadio.length > 0) {
            console.log('✅ Pagar.me provider detected in form');
            this._setupPagarmeFormFix();
        }
    },

    _setupPagarmeFormFix: function () {
        // Override the payment processing for Pagar.me to force inline
        const self = this;
        
        // Find the payment submit button and override its behavior
        const submitButton = this.$el.find('button[name="o_payment_submit_button"]');
        if (submitButton.length > 0) {
            console.log('🔧 Setting up Pagar.me payment processing override');
            
            // Store original handler
            const originalClick = submitButton.data('events') && submitButton.data('events').click;
            
            // Add our custom handler
            submitButton.off('click.pagarme_fix').on('click.pagarme_fix', function (e) {
                const selectedProvider = self.$el.find('input[name="provider_id"]:checked');
                if (selectedProvider.data('provider-code') === 'pagarme') {
                    console.log('🎯 INTERCEPTING PAGAR.ME PAYMENT CLICK!');
                    e.stopPropagation();
                    e.preventDefault();
                    self._processPagarmeInlinePayment();
                    return false;
                }
            });
        }
    },

    _onPayButtonClick: function (e) {
        const selectedProvider = this.$el.find('input[name="provider_id"]:checked');
        if (selectedProvider.data('provider-code') === 'pagarme') {
            console.log('🎯 PAGAR.ME PAYMENT BUTTON CLICKED - PROCESSING INLINE');
            e.stopPropagation();
            e.preventDefault();
            this._processPagarmeInlinePayment();
            return false;
        }
    },

    _processPagarmeInlinePayment: function () {
        console.log('💳 Processing Pagar.me inline payment...');
        
        // Force inline form rendering by triggering the correct flow
        const selectedProvider = this.$el.find('input[name="provider_id"]:checked');
        const providerId = selectedProvider.val();
        const providerCode = selectedProvider.data('provider-code');
        
        console.log('Provider ID:', providerId);
        console.log('Provider Code:', providerCode);
        
        // Look for existing inline form container
        let inlineContainer = this.$el.find(`#o_pagarme_payment_container_${providerId}`);
        if (inlineContainer.length === 0) {
            // Try alternative container IDs
            inlineContainer = this.$el.find('.o_pagarme_payment_form');
        }
        
        if (inlineContainer.length > 0) {
            console.log('✅ Found Pagar.me inline form container!');
            inlineContainer.show();
            
            // Show success message
            this._showPaymentForm(inlineContainer);
        } else {
            console.log('❌ Pagar.me inline form container not found - forcing template render');
            this._forceRenderInlineForm(providerId);
        }
    },

    _showPaymentForm: function (container) {
        // Show the payment form with a success message
        container.prepend(`
            <div class="alert alert-success" style="margin: 10px 0;">
                <strong>✅ Pagar.me Ready</strong> 
                <span style="margin-left: 10px;">Payment form loaded successfully. Enter your card details to proceed.</span>
            </div>
        `);
        
        // Focus on the first input
        const firstInput = container.find('input[type="text"]').first();
        if (firstInput.length > 0) {
            setTimeout(() => firstInput.focus(), 100);
        }
    },

    _forceRenderInlineForm: function (providerId) {
        // If inline form doesn't exist, force a page reload with inline parameter
        console.log('🔄 Forcing inline form render for provider:', providerId);
        
        // Add a debug message
        this.$el.prepend(`
            <div class="alert alert-info" style="margin: 10px 0;">
                <strong>🔧 Pagar.me Debug</strong> 
                <span style="margin-left: 10px;">Forcing inline form render. Provider ID: ${providerId}</span>
            </div>
        `);
        
        // Try to submit the form normally but with inline flag
        const form = this.$el.closest('form');
        if (form.length > 0) {
            form.append('<input type="hidden" name="force_inline" value="pagarme">');
            form.submit();
        }
    },
});

// Also register the original payment form widget for card input handling
publicWidget.registry.PagarmePaymentForm = publicWidget.Widget.extend({
    selector: '.o_pagarme_payment_form',
    events: {
        'input #pagarme_card_number': '_onCardNumberInput',
        'input #pagarme_card_expiry': '_onExpiryInput',
        'input #pagarme_card_cvv': '_onCvvInput',
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

console.log('🔧 Pagar.me payment widgets registered!');