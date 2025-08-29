/** @odoo-module **/

import checkoutForm from 'payment.checkout_form';

// Pagar.me redirect payment implementation following Adyen pattern
checkoutForm.include({
    // For redirect payment, no special JavaScript processing is needed
    // The redirect form template handles the actual redirection to Pagar.me
});

console.log('✅ Pagar.me redirect payment module loaded successfully!');