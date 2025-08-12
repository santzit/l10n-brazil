odoo.define('payment_mercado_pago_extension.mercado_pago_transparent', function(require) {
    'use strict';

    const ajax = require('web.ajax');
    const publicKey = odoo.payment_provider_mercado_pago_public_key;

    if (!publicKey) {
        console.error('Mercado Pago public key is not set.');
        return;
    }

    // Wait until DOM is ready
    require('web.dom_ready');

    // Load Mercado Pago SDK if not already loaded
    function loadMercadoPagoSdk(callback) {
        if (window.MercadoPago) {
            callback();
            return;
        }
        const script = document.createElement('script');
        script.src = 'https://sdk.mercadopago.com/js/v2';
        script.onload = callback;
        document.head.appendChild(script);
    }

    loadMercadoPagoSdk(function() {
        // Initialize MercadoPago object
        const mercadopago = new window.MercadoPago(publicKey, {
            locale: 'pt-BR',
        });

        // Create CardForm
        const cardForm = mercadopago.cardForm({
            amount: document.querySelector('[name="amount"]').value || '0',
            autoMount: true,
            form: {
                id: 'mercado_pago_checkout',
                cardholderName: {
                    id: 'form-cardholderName',
                    placeholder: 'Nome como aparece no cartão',
                },
                cardholderEmail: {
                    id: 'form-cardholderEmail',
                    placeholder: 'E-mail',
                },
                cardNumber: {
                    id: 'form-cardNumber',
                    placeholder: 'Número do cartão',
                },
                cardExpirationMonth: {
                    id: 'form-cardExpirationMonth',
                    placeholder: 'MM',
                },
                cardExpirationYear: {
                    id: 'form-cardExpirationYear',
                    placeholder: 'YY',
                },
                securityCode: {
                    id: 'form-securityCode',
                    placeholder: 'CVC',
                },
                identificationType: {
                    id: 'form-identificationType',
                    placeholder: 'Tipo de documento',
                },
                identificationNumber: {
                    id: 'form-identificationNumber',
                    placeholder: 'Número do documento',
                },
                issuer: {
                    id: 'form-issuer',
                    placeholder: 'Banco emissor',
                },
            },
            callbacks: {
                onFormMounted: function(error) {
                    if (error) {
                        console.error('Form Mounted handling error:', error);
                    }
                },
                onSubmit: function(event) {
                    event.preventDefault();
                    document.getElementById('mercado-pago-loading').style.display = 'block';

                    const cardData = cardForm.getCardFormData();
                    ajax.jsonRpc('/payment/mercado_pago/charge', 'call', {
                        token: cardData.token,
                        payment_method_id: cardData.paymentMethodId,
                        issuer_id: cardData.issuerId,
                        amount: cardData.amount,
                        email: cardData.cardholderEmail,
                        identification_type: cardData.identificationType,
                        identification_number: cardData.identificationNumber,
                        // Add other fields as needed
                    }).then(function(response) {
                        document.getElementById('mercado-pago-loading').style.display = 'none';
                        if (response.status === 'success') {
                            // Redirect or show success message
                            window.location.href = response.redirect_url || '/payment/success';
                        } else {
                            // Show error
                            alert(response.message || 'Erro ao processar pagamento.');
                        }
                    }).catch(function(error){
                        document.getElementById('mercado-pago-loading').style.display = 'none';
                        alert('Erro inesperado ao processar pagamento.');
                        console.error(error);
                    });
                },
                onFetching: function(resource) {
                    // Show loading indicator
                    document.getElementById('mercado-pago-loading').style.display = 'block';
                    return () => {
                        document.getElementById('mercado-pago-loading').style.display = 'none';
                    };
                }
            },
        });

        // Build the HTML form dynamically if not present
        if (!document.getElementById('form-cardholderName')) {
            const checkoutDiv = document.getElementById('mercado_pago_checkout');
            checkoutDiv.innerHTML = `
                <form id="mercado-pago-form">
                    <input type="text" id="form-cardholderName" placeholder="Nome como aparece no cartão" required />
                    <input type="email" id="form-cardholderEmail" placeholder="E-mail" required />
                    <input type="text" id="form-cardNumber" placeholder="Número do cartão" required />
                    <input type="text" id="form-cardExpirationMonth" placeholder="MM" required />
                    <input type="text" id="form-cardExpirationYear" placeholder="YY" required />
                    <input type="text" id="form-securityCode" placeholder="CVC" required />
                    <select id="form-identificationType"></select>
                    <input type="text" id="form-identificationNumber" placeholder="Número do documento" required />
                    <select id="form-issuer"></select>
                    <button type="submit">Pagar</button>
                </form>
                <div id="mercado-pago-loading" style="display:none;">Processando...</div>
            `;
        }
    });
});