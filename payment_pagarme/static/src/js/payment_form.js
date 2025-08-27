/** @odoo-module **/

import publicWidget from 'web.public.widget';
import core from 'web.core';
import PaymentForm from 'payment.payment_form';

const _t = core._t;

console.log('🚀 PAGAR.ME PAYMENT FORM MODULE LOADING...');

// Extend Odoo's standard PaymentForm widget for Pagar.me integration
PaymentForm.include({
    
    /**
     * Override payment processing specifically for Pagar.me provider
     */
    _processPayment: function () {
        // Check if this is a Pagar.me payment
        const selectedProvider = this.$('input[name="provider_id"]:checked');
        const providerCode = selectedProvider.data('provider');
        
        if (providerCode === 'pagarme') {
            console.log('🎯 Pagar.me payment detected - using transparent checkout');
            return this._processPagarmePayment();
        }
        
        // For other providers, use the standard payment flow
        return this._super.apply(this, arguments);
    },

    /**
     * Process Pagar.me payment using transparent checkout with card tokenization
     */
    _processPagarmePayment: function () {
        console.log('💳 Processing Pagar.me transparent payment');
        
        // Validate card data before processing
        if (!this._validatePagarmeCardData()) {
            return Promise.reject('Please fill in all required card details.');
        }
        
        // Show processing indicator
        this._showPagarmeMessage('⏳ Processing', 'Tokenizing card data...', 'info');
        
        // Get card data from form
        const cardData = this._getPagarmeCardData();
        
        // Get transaction context
        const processingData = this._getPagarmeProcessingData();
        
        if (!processingData.reference) {
            this._showPagarmeMessage('❌ Error', 'Transaction reference is missing. Please refresh and try again.', 'error');
            return Promise.reject('Missing transaction reference');
        }
        
        // Initialize Pagar.me SDK and tokenize card
        return this._tokenizeCard(cardData, processingData).then((cardHash) => {
            console.log('✅ Card tokenized successfully');
            
            // Process payment with tokenized card
            return this._submitPagarmePayment(cardHash, processingData);
        }).catch((error) => {
            console.error('❌ Pagar.me payment failed:', error);
            this._showPagarmeMessage('❌ Error', error.message || 'Payment processing failed', 'error');
            throw error;
        });
    },

    /**
     * Tokenize card using Pagar.me JavaScript SDK
     */
    _tokenizeCard: function (cardData, processingData) {
        return new Promise((resolve, reject) => {
            // Check if Pagar.me SDK is loaded
            if (typeof pagarme === 'undefined') {
                reject(new Error('Pagar.me SDK not loaded. Please refresh the page.'));
                return;
            }
            
            console.log('🔐 Tokenizing card with Pagar.me SDK');
            
            // Initialize Pagar.me client
            const client = pagarme.client.connect({
                encryption_key: processingData.encryption_key
            });
            
            // Prepare card data for tokenization
            const card = {
                card_number: cardData.number.replace(/\s/g, ''),
                card_holder_name: cardData.holderName,
                card_expiration_date: cardData.expiryMonth + cardData.expiryYear,
                card_cvv: cardData.cvv,
            };
            
            // Tokenize the card
            client.cards.create(card).then((cardResponse) => {
                console.log('✅ Card tokenization successful');
                resolve(cardResponse.card_hash);
            }).catch((error) => {
                console.error('❌ Card tokenization failed:', error);
                reject(new Error('Card tokenization failed: ' + (error.message || 'Unknown error')));
            });
        });
    },

    /**
     * Submit payment with tokenized card hash
     */
    _submitPagarmePayment: function (cardHash, processingData) {
        console.log('📤 Submitting tokenized payment to Odoo');
        
        this._showPagarmeMessage('⏳ Processing', 'Processing payment...', 'info');
        
        const paymentData = {
            reference: processingData.reference,
            provider_id: processingData.provider_id,
            access_token: processingData.access_token,
            card_hash: cardHash,
            installments: this._getPagarmeInstallments(),
        };
        
        return this._rpc({
            route: '/payment/pagarme/process_transparent',
            params: paymentData,
        }).then((result) => {
            if (result.status === 'success') {
                console.log('✅ Payment processed successfully');
                this._showPagarmeMessage('✅ Success', 'Payment completed successfully!', 'success');
                
                // Redirect to status page
                setTimeout(() => {
                    window.location.href = result.redirect_url || '/payment/status';
                }, 2000);
                
                return result;
            } else {
                throw new Error(result.message || 'Payment processing failed');
            }
        });
    },

    /**
     * Get card data from form fields
     */
    _getPagarmeCardData: function () {
        const cardNumber = this.$('#pagarme_card_number').val() || '';
        const cardHolder = this.$('#pagarme_card_holder_name').val() || '';
        const cardExpiry = this.$('#pagarme_card_expiry').val() || '';
        const cardCvv = this.$('#pagarme_card_cvv').val() || '';
        
        // Parse expiry date
        const expiryParts = cardExpiry.split('/');
        const expiryMonth = expiryParts[0] || '';
        const expiryYear = expiryParts[1] ? '20' + expiryParts[1] : '';
        
        return {
            number: cardNumber,
            holderName: cardHolder,
            expiryMonth: expiryMonth,
            expiryYear: expiryYear,
            cvv: cardCvv,
        };
    },

    /**
     * Get processing data (transaction context)
     */
    _getPagarmeProcessingData: function () {
        return {
            reference: this.$('input[name="reference"]').val() || '',
            provider_id: this.$('input[name="provider_id"]:checked').val() || '',
            access_token: this.$('input[name="access_token"]').val() || '',
            encryption_key: this.$('input[name="encryption_key"]').val() || '',
        };
    },

    /**
     * Get selected installments
     */
    _getPagarmeInstallments: function () {
        return parseInt(this.$('#pagarme_installments').val() || '1');
    },

    /**
     * Validate Pagar.me card data
     */
    _validatePagarmeCardData: function () {
        const cardData = this._getPagarmeCardData();
        
        const isValid = (
            cardData.number.replace(/\s/g, '').length >= 13 &&
            cardData.holderName.trim().length >= 2 &&
            cardData.expiryMonth.length === 2 &&
            cardData.expiryYear.length === 4 &&
            cardData.cvv.length >= 3
        );
        
        if (!isValid) {
            this._showPagarmeMessage('❌ Error', 'Please fill in all required card details correctly.', 'error');
        }
        
        return isValid;
    },

    /**
     * Show status messages for Pagar.me
     */
    _showPagarmeMessage: function (title, message, type) {
        // Remove existing messages
        this.$('.pagarme-status-message').remove();
        
        const alertClass = type === 'success' ? 'alert-success' : 
                          type === 'warning' ? 'alert-warning' : 
                          type === 'info' ? 'alert-info' : 'alert-danger';
        
        const messageHtml = `
            <div class="alert ${alertClass} pagarme-status-message" style="margin: 10px 0;">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${title}</strong>
                        <span class="ml-2">${message}</span>
                    </div>
                    <button type="button" class="close" data-dismiss="alert">
                        <span>&times;</span>
                    </button>
                </div>
            </div>
        `;
        
        this.$('.o_pagarme_payment_form').prepend(messageHtml);
        
        // Auto-remove success and info messages
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                this.$('.pagarme-status-message').fadeOut();
            }, 5000);
        }
    },
});

// Widget for Pagar.me specific form enhancements
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