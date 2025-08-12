odoo.define('payment_mercado_pago_extension.mercado_pago_transparent', function(require) {
    'use strict';

    var publicKey = odoo.payment_provider_mercado_pago_public_key;
    var mercadopago;
    if (publicKey) {
        mercadopago = new MercadoPago(publicKey);
        // The rest of your initialization logic for transparent checkout
        // e.g., creating cardForm, handling responses, etc.
    }
});