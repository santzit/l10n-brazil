odoo.define('payment_mercado_pago_extension.mercado_pago_transparent', function(require) {
    'use strict';

    const ajax = require('web.ajax');
    const core = require('web.core');
    
    // Get public key from global variable set by template
    const publicKey = window.odoo_mercado_pago_public_key;

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
        script.onerror = function() {
            console.error('Failed to load Mercado Pago SDK');
        };
        document.head.appendChild(script);
    }

    function initializeMercadoPago() {
        const checkoutDiv = document.getElementById('mercado_pago_checkout');
        if (!checkoutDiv) {
            return;
        }

        // Initialize MercadoPago object
        const mercadopago = new window.MercadoPago(publicKey, {
            locale: 'pt-BR',
        });

        // Build the HTML form if not present
        const formContainer = document.getElementById('mercado-pago-form-container');
        if (formContainer && !document.getElementById('form-cardholderName')) {
            formContainer.innerHTML = `
                <form id="mercado-pago-form" class="row">
                    <div class="col-md-6 mb-3">
                        <label for="form-cardholderName" class="form-label">Nome como aparece no cartão</label>
                        <input type="text" id="form-cardholderName" class="form-control" placeholder="Nome completo" required />
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="form-cardholderEmail" class="form-label">E-mail</label>
                        <input type="email" id="form-cardholderEmail" class="form-control" placeholder="seu@email.com" required />
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="form-cardNumber" class="form-label">Número do cartão</label>
                        <input type="text" id="form-cardNumber" class="form-control" placeholder="0000 0000 0000 0000" required />
                    </div>
                    <div class="col-md-3 mb-3">
                        <label for="form-cardExpirationMonth" class="form-label">Mês</label>
                        <input type="text" id="form-cardExpirationMonth" class="form-control" placeholder="MM" maxlength="2" required />
                    </div>
                    <div class="col-md-3 mb-3">
                        <label for="form-cardExpirationYear" class="form-label">Ano</label>
                        <input type="text" id="form-cardExpirationYear" class="form-control" placeholder="YY" maxlength="2" required />
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="form-securityCode" class="form-label">CVC</label>
                        <input type="text" id="form-securityCode" class="form-control" placeholder="123" maxlength="4" required />
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="form-identificationType" class="form-label">Tipo de documento</label>
                        <select id="form-identificationType" class="form-control" required>
                            <option value="">Selecionar...</option>
                            <option value="CPF">CPF</option>
                            <option value="CNPJ">CNPJ</option>
                        </select>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="form-identificationNumber" class="form-label">Número do documento</label>
                        <input type="text" id="form-identificationNumber" class="form-control" placeholder="000.000.000-00" required />
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="form-issuer" class="form-label">Banco emissor</label>
                        <select id="form-issuer" class="form-control" required>
                            <option value="">Selecionar banco...</option>
                        </select>
                    </div>
                    <div class="col-12">
                        <button type="submit" class="btn btn-primary btn-lg w-100">
                            <i class="fa fa-credit-card"></i> Finalizar Pagamento
                        </button>
                    </div>
                </form>
            `;
        }

        // Create CardForm
        const amountInput = document.querySelector('[name="amount"]');
        const cardForm = mercadopago.cardForm({
            amount: amountInput ? amountInput.value : '0',
            autoMount: true,
            form: {
                id: 'mercado-pago-form',
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
                    } else {
                        console.log('Mercado Pago form mounted successfully');
                    }
                },
                onSubmit: function(event) {
                    event.preventDefault();
                    const loadingDiv = document.getElementById('mercado-pago-loading');
                    loadingDiv.style.display = 'block';

                    const cardData = cardForm.getCardFormData();
                    
                    // Get transaction ID from form or session
                    const txId = document.querySelector('[name="tx_id"]') ? 
                               document.querySelector('[name="tx_id"]').value : 
                               null;

                    ajax.jsonRpc('/payment/mercado_pago/charge', 'call', {
                        tx_id: txId,
                        token: cardData.token,
                        payment_method_id: cardData.paymentMethodId,
                        issuer_id: cardData.issuerId,
                        amount: cardData.amount,
                        email: cardData.cardholderEmail,
                        identification_type: cardData.identificationType,
                        identification_number: cardData.identificationNumber,
                    }).then(function(response) {
                        loadingDiv.style.display = 'none';
                        if (response.status === 'success') {
                            // Redirect or show success message
                            window.location.href = response.redirect_url || '/payment/success';
                        } else {
                            // Show error
                            alert(response.message || 'Erro ao processar pagamento.');
                        }
                    }).catch(function(error){
                        loadingDiv.style.display = 'none';
                        alert('Erro inesperado ao processar pagamento.');
                        console.error('Payment error:', error);
                    });
                },
                onFetching: function(resource) {
                    // Show loading indicator during API calls
                    const loadingDiv = document.getElementById('mercado-pago-loading');
                    if (loadingDiv) {
                        loadingDiv.style.display = 'block';
                    }
                    return () => {
                        if (loadingDiv) {
                            loadingDiv.style.display = 'none';
                        }
                    };
                }
            },
        });
    }

    // Initialize when DOM is ready and SDK is loaded
    loadMercadoPagoSdk(initializeMercadoPago);
});