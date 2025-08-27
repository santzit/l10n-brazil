// Basic Pagar.me form enhancements without complex module dependencies
(function () {
    'use strict';
    
    console.log('🚀 Pagar.me payment form loading...');

    function formatCardNumber(input) {
        let value = input.value.replace(/\s/g, '').replace(/\D/g, '');
        value = value.replace(/(\d{4})(?=\d)/g, '$1 ');
        input.value = value;
    }

    function formatExpiry(input) {
        let value = input.value.replace(/\D/g, '');
        if (value.length >= 2) {
            value = value.substring(0, 2) + '/' + value.substring(2, 4);
        }
        input.value = value;
    }

    function formatCvv(input) {
        input.value = input.value.replace(/\D/g, '');
    }

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        // Card number formatting
        const cardNumberInput = document.getElementById('pagarme_card_number');
        if (cardNumberInput) {
            cardNumberInput.addEventListener('input', function(e) {
                formatCardNumber(e.target);
            });
        }

        // Expiry formatting
        const expiryInput = document.getElementById('pagarme_card_expiry');
        if (expiryInput) {
            expiryInput.addEventListener('input', function(e) {
                formatExpiry(e.target);
            });
        }

        // CVV formatting
        const cvvInput = document.getElementById('pagarme_card_cvv');
        if (cvvInput) {
            cvvInput.addEventListener('input', function(e) {
                formatCvv(e.target);
            });
        }

        console.log('✅ Pagar.me form enhancements initialized');
    });

})();