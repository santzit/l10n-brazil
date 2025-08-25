/** @odoo-module */

import checkoutForm from 'payment.checkout_form';
import manageForm from 'payment.manage_form';

const pagarmeTransparentCheckoutMixin = {

    /**
     * Check if template is rendered when we click pay
     */
    async _processPayment(provider, paymentOptionId, flow) {
        console.log('Pagar.me: _processPayment called with:', { provider, paymentOptionId, flow });
        
        if (provider !== 'pagarme') {
            return this._super(...arguments);
        }
        
        // Enhanced debugging for template detection
        console.log('=== PAGAR.ME DEBUG START ===');
        console.log('Provider:', provider);
        console.log('Payment Option ID:', paymentOptionId);
        console.log('Flow:', flow);
        
        // Look for the Pagar.me container
        const pagarmeContainer = this.$('[id*="o_pagarme_payment_container"]');
        console.log('Pagar.me containers found:', pagarmeContainer.length);
        
        if (pagarmeContainer.length > 0) {
            console.log('Container ID:', pagarmeContainer.attr('id'));
            console.log('Container content:', pagarmeContainer.html());
        }
        
        // Check for debug template
        const templateCheck = this.$('[style*="background: green"]');
        const successCheck = this.$('div:contains("PAGAR.ME TEMPLATE RENDERED SUCCESSFULLY")');
        
        console.log('Debug template elements found:', templateCheck.length);
        console.log('Success message elements found:', successCheck.length);
        
        // List all payment-related containers for debugging
        const allPaymentContainers = this.$('[class*="payment"], [id*="payment"], [class*="o_"], [id*="o_"]');
        console.log('All payment-related elements found:', allPaymentContainers.length);
        allPaymentContainers.each(function(i, el) {
            console.log(`Element ${i}:`, $(el).attr('class'), $(el).attr('id'));
        });
        
        console.log('=== PAGAR.ME DEBUG END ===');
        
        if (templateCheck.length > 0 || successCheck.length > 0 || pagarmeContainer.length > 0) {
            console.log('SUCCESS: Pagar.me template was rendered!');
            console.log('Template content:', templateCheck.text() || successCheck.text() || pagarmeContainer.text());
            
            // Show success message
            alert('✅ Template está funcionando! Container encontrado.');
            return Promise.resolve();
        } else {
            console.error('FAILED: Pagar.me template was NOT rendered!');
            
            // Show detailed error message
            alert('❌ Template não foi renderizado. Verifique os logs do console para mais detalhes.');
            this._displayError('Erro de Configuração', 'Template de pagamento não foi renderizado');
            return Promise.reject("Template not rendered");
        }
    }
};

checkoutForm.include(pagarmeTransparentCheckoutMixin);
manageForm.include(pagarmeTransparentCheckoutMixin);