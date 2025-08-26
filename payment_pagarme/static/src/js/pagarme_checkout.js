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
        
        // CRITICAL: Intercept all pay button clicks to prevent redirect processing
        this._interceptPayButtonClicks();
        
        return this._super.apply(this, arguments);
    },

    _interceptPayButtonClicks: function () {
        console.log('🔒 Setting up pay button interception to prevent redirect processing');
        
        // Find and intercept the main "Pay" button clicks
        const self = this;
        
        // Use document event delegation to catch pay button clicks
        $(document).on('click', 'button[name="o_payment_submit_button"], .btn[name="o_payment_submit_button"], input[name="o_payment_submit_button"]', function (ev) {
            // Check if this is for Pagar.me provider
            const pagarmeForm = $(this).closest('form').find('.o_pagarme_payment_form');
            if (pagarmeForm.length > 0) {
                console.log('🛑 Intercepted pay button click for Pagar.me - preventing redirect processing');
                ev.preventDefault();
                ev.stopPropagation();
                ev.stopImmediatePropagation();
                
                // Process payment via our inline method
                self._processInlinePayment();
                return false;
            }
        });
        
        console.log('✅ Pay button interception setup complete');
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
        
        // Split expiry into month and year components for hidden fields
        if (value.length === 5 && value.includes('/')) {
            const parts = value.split('/');
            const monthField = document.getElementById('pagarme_card_exp_month');
            const yearField = document.getElementById('pagarme_card_exp_year');
            if (monthField && yearField) {
                monthField.value = parts[0];
                yearField.value = '20' + parts[1]; // Convert YY to YYYY
            }
        }
    },

    _onCvvInput: function (ev) {
        const input = ev.currentTarget;
        input.value = input.value.replace(/\D/g, '');
    },

    _onFormSubmit: function (ev) {
        console.log('💳 Pagar.me form submitted');
        ev.preventDefault(); // Always prevent default form submission
        ev.stopPropagation();
        
        this._processInlinePayment();
    },

    _processInlinePayment: function () {
        console.log('💳 Processing Pagar.me inline payment');
        
        // Validate form before submission
        if (!this._validateForm()) {
            this._showMessage('❌ Error', 'Please fill in all required card details.', 'error');
            return false;
        }
        
        console.log('✅ Form validation passed, processing payment via AJAX');
        this._showMessage('⏳ Processing', 'Processing payment...', 'info');
        
        // Process payment via AJAX to avoid redirect form processing
        this._processPayment();
    },

    _processPayment: function () {
        console.log('📤 Processing payment via AJAX to avoid redirect form processing');
        
        // Gather form data
        const formData = {
            reference: $('input[name="reference"]').val(),
            provider_id: $('input[name="provider_id"]').val(),
            access_token: $('input[name="access_token"]').val(),
            pagarme_card_number: $('#pagarme_card_number').val().replace(/\s/g, ''),
            pagarme_card_holder_name: $('#pagarme_card_holder').val(),
            pagarme_card_exp_month: $('#pagarme_card_exp_month').val(),
            pagarme_card_exp_year: $('#pagarme_card_exp_year').val(),
            pagarme_card_cvv: $('#pagarme_card_cvv').val(),
            pagarme_installments: 1,
        };
        
        console.log('📋 Form data prepared:', {
            reference: formData.reference,
            provider_id: formData.provider_id,
            has_access_token: !!formData.access_token,
            card_ending: formData.pagarme_card_number.slice(-4),
            holder_name: formData.pagarme_card_holder_name,
            exp_date: formData.pagarme_card_exp_month + '/' + formData.pagarme_card_exp_year,
        });
        
        // Use AJAX to submit payment data to avoid Odoo's redirect processing
        $.ajax({
            url: '/payment/pagarme/payment',
            type: 'POST',
            data: formData,
            timeout: 30000,
            success: (response) => {
                console.log('✅ Payment processed successfully');
                this._showMessage('✅ Success', 'Payment completed successfully!', 'success');
                // Redirect to payment status page
                setTimeout(() => {
                    window.location.href = '/payment/status';
                }, 2000);
            },
            error: (xhr, status, error) => {
                console.error('❌ Payment processing failed:', error);
                const errorMsg = xhr.responseJSON?.message || 'Payment processing failed. Please try again.';
                this._showMessage('❌ Error', errorMsg, 'error');
            }
        });
    },

    _validateForm: function () {
        const cardNumber = document.getElementById('pagarme_card_number').value.replace(/\s/g, '');
        const cardHolder = document.getElementById('pagarme_card_holder').value.trim();
        const cardExpiry = document.getElementById('pagarme_card_expiry').value;
        const cardCvv = document.getElementById('pagarme_card_cvv').value;
        
        return cardNumber.length >= 13 && 
               cardHolder.length >= 2 && 
               cardExpiry.length === 5 && 
               cardCvv.length >= 3;
    },

    _showMessage: function (title, message, type) {
        const existingMessage = document.querySelector('.pagarme-status-message');
        if (existingMessage) {
            existingMessage.remove();
        }
        
        const container = this.$el[0];
        if (!container) return;
        
        const alertClass = type === 'success' ? 'alert-success' : 
                          type === 'warning' ? 'alert-warning' : 
                          type === 'info' ? 'alert-info' : 'alert-danger';
        const icon = type === 'success' ? '✅' : 
                    type === 'warning' ? '⚠️' : 
                    type === 'info' ? 'ℹ️' : '❌';
        
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
        
        // Auto-remove success and info messages
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                if (messageDiv.parentElement) {
                    messageDiv.remove();
                }
            }, 5000);
        }
    },
});

console.log('🔧 Pagar.me payment form widget registered!');