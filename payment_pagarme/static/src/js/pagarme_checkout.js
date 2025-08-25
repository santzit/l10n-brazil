/** @odoo-module */

import checkoutForm from 'payment.checkout_form';
import manageForm from 'payment.manage_form';

const pagarmeTransparentCheckoutMixin = {

    /**
     * Check if template is rendered when we click pay
     */
    async _processPayment(provider, paymentOptionId, flow) {
        console.log('Pagar.me: _processPayment called with:', { provider, paymentOptionId, flow });
        
        // Critical debug: Check if template was rendered
        const templateCheck = this.$('[style*="background: red"]');
        if (templateCheck.length > 0) {
            console.log('SUCCESS: Pagar.me template was rendered!');
            console.log('Template content:', templateCheck.text());
        } else {
            console.error('FAILED: Pagar.me template was NOT rendered!');
            console.error('This means _should_build_inline_form() or _get_inline_form_template() is not working');
        }
        
        if (provider !== 'pagarme') {
            return this._super(...arguments);
        }

        // For now, just show an alert to confirm the template is working
        if (templateCheck.length > 0) {
            alert('Template está funcionando! Provider ID: ' + paymentOptionId);
        } else {
            alert('Template NÃO está funcionando - métodos inline não foram chamados');
            this._displayError('Erro de Configuração', 'Template de pagamento não foi renderizado');
            return Promise.reject("Template not rendered");
        }
        
        return Promise.resolve();
    }
};

checkoutForm.include(pagarmeTransparentCheckoutMixin);
manageForm.include(pagarmeTransparentCheckoutMixin);