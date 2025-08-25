/** @odoo-module **/

console.log('🚀 PAGAR.ME MODULE LOADING...');

// Enhanced approach - check for template and provide comprehensive debugging
(function() {
    'use strict';
    
    let checkStarted = false;
    
    function startTemplateCheck() {
        if (checkStarted) return;
        checkStarted = true;
        
        console.log('📦 Pagar.me template checker starting...');
        
        // Immediate check
        checkForTemplate();
        
        // Periodic checks
        let checkCount = 0;
        const maxChecks = 30; // Increased check count
        
        const checkInterval = setInterval(() => {
            checkCount++;
            console.log(`🔍 Pagar.me template check #${checkCount}`);
            
            if (checkForTemplate()) {
                clearInterval(checkInterval);
                return;
            }
            
            if (checkCount >= maxChecks) {
                console.log('⏰ TIMEOUT: Template check stopped after', maxChecks, 'attempts');
                showMessage('❌ Template não encontrado', 'Template Pagar.me não foi renderizado após 15 segundos. Verifique se o provider está ativo e configurado corretamente.', 'warning');
                clearInterval(checkInterval);
            }
        }, 500);
        
        // Also check when clicking pay buttons
        document.addEventListener('click', function(event) {
            const target = event.target;
            if (target && (
                target.textContent?.includes('Pay') || 
                target.textContent?.includes('Pagar') ||
                target.classList.contains('btn-payment') ||
                target.closest('[name="o_payment_submit_button"]')
            )) {
                console.log('🔘 Pay button clicked, checking for template...');
                setTimeout(() => checkForTemplate(), 100);
                setTimeout(() => checkForTemplate(), 500);
                setTimeout(() => checkForTemplate(), 1000);
            }
        });
    }
    
    function checkForTemplate() {
        // Look for various Pagar.me indicators
        const indicators = {
            container: document.querySelector('[id*="o_pagarme_payment_container"]'),
            form: document.querySelector('.o_pagarme_payment_form'),
            debugTemplate: document.querySelector('[style*="background: #28a745"]'),
            cardField: document.getElementById('pagarme_card_number'),
            successBanner: document.querySelector('[style*="PAGAR.ME TEMPLATE RENDERED"]')
        };
        
        const found = Object.values(indicators).some(el => el !== null);
        
        if (found) {
            console.log('✅ PAGAR.ME TEMPLATE DETECTED!');
            Object.entries(indicators).forEach(([key, element]) => {
                if (element) {
                    console.log(`✓ ${key}:`, element.id || element.className, element.tagName);
                }
            });
            
            showMessage('✅ Template Funcionando!', 'Template Pagar.me foi detectado e renderizado com sucesso! Os campos de cartão estão disponíveis.', 'success');
            return true;
        }
        
        return false;
    }
    
    function showMessage(title, message, type) {
        const existingMessage = document.querySelector('.pagarme-status-message');
        if (existingMessage) {
            existingMessage.remove();
        }
        
        const container = document.querySelector('.o_payment_form') || 
                         document.querySelector('#payment_method') ||
                         document.querySelector('main') ||
                         document.body;
        
        if (!container) return;
        
        const alertClass = type === 'success' ? 'alert-success' : type === 'warning' ? 'alert-warning' : 'alert-danger';
        const icon = type === 'success' ? '✅' : type === 'warning' ? '⚠️' : '❌';
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `alert ${alertClass} pagarme-status-message`;
        messageDiv.style.cssText = 'margin: 15px 0; padding: 15px; border-radius: 8px; font-weight: bold; border: 2px solid;';
        messageDiv.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>${icon} ${title}</strong><br>
                    <span style="font-weight: normal;">${message}</span>
                </div>
                <button type="button" style="background: none; border: none; font-size: 18px; cursor: pointer;" onclick="this.closest('.pagarme-status-message').remove()">&times;</button>
            </div>
        `;
        
        container.insertBefore(messageDiv, container.firstChild);
        
        // Auto-remove success messages
        if (type === 'success') {
            setTimeout(() => {
                if (messageDiv.parentElement) {
                    messageDiv.remove();
                }
            }, 15000);
        }
    }
    
    // Start checks when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startTemplateCheck);
    } else {
        startTemplateCheck();
    }
    
    // Also start when page is fully loaded (for dynamic content)
    window.addEventListener('load', startTemplateCheck);
    
})();

console.log('🔧 Pagar.me template checker loaded and ready!');