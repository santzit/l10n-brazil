/** @odoo-module */

console.log('🚀 PAGAR.ME MODULE LOADING...');

import checkoutForm from 'payment.checkout_form';
import manageForm from 'payment.manage_form';

console.log('📦 Payment modules imported:', { checkoutForm, manageForm });

const pagarmeTransparentCheckoutMixin = {

    /**
     * Process payment for Pagar.me provider
     */
    async _processPayment(provider, paymentOptionId, flow) {
        console.log('=== PAGAR.ME PAYMENT DEBUG START ===');
        console.log('_processPayment called with:', { provider, paymentOptionId, flow });
        
        // Always call super for non-Pagar.me providers
        if (provider !== 'pagarme') {
            console.log('Not a Pagar.me provider, calling super...');
            return this._super(...arguments);
        }
        
        console.log('🎯 PAGAR.ME PROVIDER DETECTED!');
        console.log('Provider:', provider);
        console.log('Payment Option ID:', paymentOptionId);
        console.log('Flow:', flow);
        
        // Enhanced debugging for DOM and template detection
        console.log('=== DOM DEBUG START ===');
        
        // Check for any Pagar.me related elements
        const allElements = document.querySelectorAll('*');
        let pagarmeElements = [];
        allElements.forEach(el => {
            if (el.id && el.id.includes('pagarme')) {
                pagarmeElements.push(el);
            }
            if (el.className && el.className.includes && el.className.includes('pagarme')) {
                pagarmeElements.push(el);
            }
        });
        
        console.log('Found Pagar.me elements in DOM:', pagarmeElements.length);
        pagarmeElements.forEach((el, i) => {
            console.log(`Element ${i}:`, el.id, el.className, el.outerHTML.substring(0, 100));
        });
        
        // Look for the specific container
        const container = document.getElementById(`o_pagarme_payment_container_${paymentOptionId}`);
        console.log('Looking for container ID:', `o_pagarme_payment_container_${paymentOptionId}`);
        console.log('Container found:', container);
        
        if (container) {
            console.log('✅ CONTAINER FOUND!');
            console.log('Container HTML:', container.outerHTML);
        }
        
        // Look for debug template
        const debugTemplate = document.querySelector('[style*="background: red"]');
        console.log('Debug template found:', debugTemplate);
        
        if (debugTemplate) {
            console.log('✅ DEBUG TEMPLATE FOUND!');
            console.log('Template content:', debugTemplate.outerHTML);
        }
        
        // Check for form fields
        const cardNumberField = document.getElementById('pagarme_card_number');
        console.log('Card number field found:', cardNumberField);
        
        console.log('=== DOM DEBUG END ===');
        
        // Determine if template was rendered
        if (container || debugTemplate || cardNumberField) {
            console.log('🎉 SUCCESS: Pagar.me template was rendered!');
            
            // Show success message
            this._displaySuccess('✅ Template funcionando!', 'Pagar.me template foi renderizado com sucesso!');
            return Promise.resolve();
        } else {
            console.error('❌ FAILED: Pagar.me template was NOT rendered!');
            console.error('Expected container ID:', `o_pagarme_payment_container_${paymentOptionId}`);
            
            // List all payment-related elements for debugging
            const paymentElements = document.querySelectorAll('[class*="payment"], [id*="payment"], [class*="o_"], [id*="o_"]');
            console.log('All payment/odoo elements found:', paymentElements.length);
            paymentElements.forEach((el, i) => {
                if (i < 10) { // Limit output
                    console.log(`Payment element ${i}:`, el.tagName, el.className, el.id);
                }
            });
            
            // Show detailed error message
            this._displayError('Erro de Template', 'Template de pagamento Pagar.me não foi renderizado. Verifique a configuração do provider.');
            return Promise.reject("Pagar.me template not rendered");
        }
    },

    /**
     * Display success message
     */
    _displaySuccess(title, message) {
        if (this.$el) {
            const successDiv = $(`
                <div class="alert alert-success alert-dismissible" style="margin: 10px 0;">
                    <button type="button" class="close" data-dismiss="alert">&times;</button>
                    <strong>${title}</strong> ${message}
                </div>
            `);
            this.$el.prepend(successDiv);
            setTimeout(() => successDiv.fadeOut(), 5000);
        }
    },

    /**
     * Display error message  
     */
    _displayError(title, message) {
        if (this.$el) {
            const errorDiv = $(`
                <div class="alert alert-danger alert-dismissible" style="margin: 10px 0;">
                    <button type="button" class="close" data-dismiss="alert">&times;</button>
                    <strong>${title}</strong> ${message}
                </div>
            `);
            this.$el.prepend(errorDiv);
        }
    }
};

// Apply the mixin to both checkout and manage forms
checkoutForm.include(pagarmeTransparentCheckoutMixin);
manageForm.include(pagarmeTransparentCheckoutMixin);

console.log('🔧 Pagar.me payment mixin loaded and applied!');