/** @odoo-module **/

console.log('🚀 PAGAR.ME MODULE LOADING...');

// Simple approach - just check if template is rendered without complex widget overrides
(function() {
    'use strict';
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPagarmeCheck);
    } else {
        initPagarmeCheck();
    }
    
    function initPagarmeCheck() {
        console.log('📦 Pagar.me DOM check initialized');
        
        // Check periodically for Pagar.me template
        let checkCount = 0;
        const maxChecks = 20;
        
        const checkInterval = setInterval(() => {
            checkCount++;
            
            // Look for Pagar.me container or template
            const pagarmeContainer = document.querySelector('[id*="o_pagarme_payment_container"]');
            const pagarmeForm = document.querySelector('.o_pagarme_payment_form');
            const debugTemplate = document.querySelector('[style*="background: #28a745"]');
            
            if (pagarmeContainer || pagarmeForm || debugTemplate) {
                console.log('✅ PAGAR.ME TEMPLATE DETECTED!');
                if (pagarmeContainer) console.log('Container found:', pagarmeContainer.id);
                if (pagarmeForm) console.log('Form found:', pagarmeForm.className);
                if (debugTemplate) console.log('Debug template found!');
                
                // Show success banner
                showMessage('✅ Template Funcionando!', 'Pagar.me template foi detectado com sucesso!', 'success');
                clearInterval(checkInterval);
                return;
            }
            
            if (checkCount >= maxChecks) {
                console.log('❌ PAGAR.ME TEMPLATE NOT FOUND after', maxChecks, 'checks');
                showMessage('❌ Template não encontrado', 'Template Pagar.me não foi renderizado. Verifique a configuração do provider.', 'error');
                clearInterval(checkInterval);
            }
        }, 500);
    }
    
    function showMessage(title, message, type) {
        // Try to find a suitable container for the message
        const paymentForm = document.querySelector('.o_payment_form') || 
                           document.querySelector('#payment_method') ||
                           document.querySelector('main') ||
                           document.body;
        
        if (!paymentForm) return;
        
        const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
        const icon = type === 'success' ? '✅' : '❌';
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `alert ${alertClass} alert-dismissible`;
        messageDiv.style.cssText = 'margin: 10px 0; padding: 15px; border-radius: 5px;';
        messageDiv.innerHTML = `
            <button type="button" class="close" onclick="this.parentElement.remove()">&times;</button>
            <strong>${icon} ${title}</strong><br>
            ${message}
        `;
        
        // Insert at the beginning of the payment form
        paymentForm.insertBefore(messageDiv, paymentForm.firstChild);
        
        // Auto-remove success messages after 10 seconds
        if (type === 'success') {
            setTimeout(() => {
                if (messageDiv.parentElement) {
                    messageDiv.remove();
                }
            }, 10000);
        }
    }
})();

console.log('🔧 Pagar.me template checker loaded!');