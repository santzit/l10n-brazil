/** @odoo-module */

console.log('🚀 PAGAR.ME MODULE LOADING...');

/** @odoo-module **/

import publicWidget from 'web.public.widget';

console.log('🚀 PAGAR.ME MODULE LOADING...');

const PagarmePaymentForm = publicWidget.Widget.extend({
    selector: '.o_payment_form',
    
    start: function() {
        console.log('📦 Pagar.me payment form widget started');
        this._super.apply(this, arguments);
        this._setupPagarmeHandling();
    },
    
    _setupPagarmeHandling: function() {
        // Override the payment processing for Pagar.me
        const originalProcessPayment = this._processPayment;
        
        this._processPayment = async function(provider, paymentOptionId, flow) {
            console.log('=== PAGAR.ME PAYMENT DEBUG START ===');
            console.log('_processPayment called with:', { provider, paymentOptionId, flow });
            
            // Always call super for non-Pagar.me providers
            if (provider !== 'pagarme') {
                console.log('Not a Pagar.me provider, calling super...');
                return originalProcessPayment.call(this, provider, paymentOptionId, flow);
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
            
            // Try multiple container ID patterns to find the template
            let container = null;
            const possibleIds = [
                `o_pagarme_payment_container_${paymentOptionId}`,
                `o_pagarme_payment_container_${provider}`,
                `o_pagarme_payment_container_pagarme`,
            ];
            
            console.log('Trying container IDs:', possibleIds);
            
            for (const containerId of possibleIds) {
                container = document.getElementById(containerId);
                console.log(`Looking for container ID: ${containerId} - Found:`, !!container);
                if (container) {
                    console.log('✅ CONTAINER FOUND with ID:', containerId);
                    console.log('Container HTML:', container.outerHTML);
                    break;
                }
            }
            
            // Look for debug template (green background for enhanced visibility)
            const debugTemplate = document.querySelector('[style*="background: #28a745"]');
            console.log('Debug template found:', debugTemplate);
            
            if (debugTemplate) {
                console.log('✅ DEBUG TEMPLATE FOUND!');
                console.log('Template content:', debugTemplate.outerHTML);
            } else {
                console.log('❌ Green debug template NOT found');
                // Also check for any Pagar.me template
                const anyPagarmeTemplate = document.querySelector('.o_pagarme_payment_form');
                if (anyPagarmeTemplate) {
                    console.log('✅ Found Pagar.me template by class:', anyPagarmeTemplate.outerHTML);
                    container = anyPagarmeTemplate;
                }
            }
            
            // Check for form fields
            const cardNumberField = document.getElementById('pagarme_card_number');
            console.log('Card number field found:', cardNumberField);
            
            console.log('=== DOM DEBUG END ===');
            
            // Determine if template was rendered
            if (container || debugTemplate || cardNumberField) {
                console.log('🎉 SUCCESS: Pagar.me template was rendered!');
                
                // Show success message with green styling
                this._displaySuccess('✅ Template Funcionando!', 'Pagar.me template foi renderizado com sucesso!');
                return Promise.resolve();
            } else {
                console.error('❌ FAILED: Pagar.me template was NOT rendered!');
                console.error('Expected container ID:', `o_pagarme_payment_container_${paymentOptionId}`);
                
                // List all payment-related elements for debugging
                const paymentElements = document.querySelectorAll('[class*="payment"], [id*="payment"], [class*="o_"], [id*="o_"]');
                console.log('All payment/odoo elements found:', paymentElements.length);
                paymentElements.forEach((el, i) => {
                    if (i < 15) { // Increase limit to see more elements
                        console.log(`Payment element ${i}:`, el.tagName, el.className, el.id);
                    }
                });
                
                // Show detailed error message
                this._displayError('❌ Erro de Template', 'Template de pagamento Pagar.me não foi renderizado. Verifique os logs do servidor Odoo para verificar se os métodos inline form estão sendo chamados.');
                return Promise.reject("Pagar.me template not rendered");
            }
        }.bind(this);
    },

    /**
     * Display success message
     */
    _displaySuccess: function(title, message) {
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
    _displayError: function(title, message) {
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
});

publicWidget.registry.PagarmePaymentForm = PagarmePaymentForm;

console.log('🔧 Pagar.me payment widget registered!');