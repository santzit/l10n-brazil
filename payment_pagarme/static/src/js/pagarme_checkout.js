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
        
        // Critical debug: Check if template was rendered
        const templateCheck = this.$('[style*="background: red"]');
        const successCheck = this.$('div:contains("PAGAR.ME TEMPLATE RENDERED SUCCESSFULLY")');
        
        if (templateCheck.length > 0 || successCheck.length > 0) {
            console.log('SUCCESS: Pagar.me template was rendered!');
            console.log('Template content:', templateCheck.text() || successCheck.text());
            
            // Show success message
            alert('✅ Template está funcionando! Provider ID: ' + paymentOptionId);
            return Promise.resolve();
        } else {
            console.error('FAILED: Pagar.me template was NOT rendered!');
            console.error('Available payment containers:', this.$('[class*="payment"]').length);
            console.error('All divs with background styles:', this.$('div[style*="background"]').length);
            
            // Show error message
            alert('❌ Template NÃO está funcionando - métodos inline não foram chamados');
            this._displayError('Erro de Configuração', 'Template de pagamento não foi renderizado');
            return Promise.reject("Template not rendered");
        }
    }
};

checkoutForm.include(pagarmeTransparentCheckoutMixin);
manageForm.include(pagarmeTransparentCheckoutMixin);