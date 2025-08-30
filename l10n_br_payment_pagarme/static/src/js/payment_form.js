/** @odoo-module **/

import checkoutForm from 'payment.checkout_form';
import manageForm from 'payment.manage_form';

const pagarmePaymentMixin = {

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Process payment with Pagar.me using direct payment approach.
     *
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} code - The code of the provider
     * @param {number} providerId - The id of the provider handling the transaction
     * @param {object} processingValues - The processing values of the transaction
     * @return {Promise}
     */
    _processDirectPayment: function (code, providerId, processingValues) {
        if (code !== 'pagarme') {
            return this._super(...arguments);
        }

        console.log('Pagar.me: Processing direct payment for provider ID:', providerId);
        
        // Get card data from form
        const cardData = this._getCardDataFromForm();
        if (!cardData) {
            return Promise.reject(new Error('Invalid card data'));
        }

        // Process payment with card data
        return this._rpc({
            route: '/payment/pagarme/payment',
            params: {
                'reference': processingValues.reference,
                'card_holder_name': cardData.holderName,
                'card_number': cardData.number,
                'card_expiry_month': cardData.expiryMonth,
                'card_expiry_year': cardData.expiryYear,
                'card_cvv': cardData.cvv,
                'amount': processingValues.amount,
                'currency': processingValues.currency,
            },
        }).then((result) => {
            if (result.error) {
                this._displayError('Erro no Pagamento', result.error);
                return Promise.reject(new Error(result.error));
            } else {
                console.log('Pagar.me: Payment processed successfully');
                window.location = '/payment/status';
                return result;
            }
        }).catch((error) => {
            console.error('Pagar.me: Payment failed:', error);
            this._displayError(
                'Erro no Pagamento',
                'Ocorreu um erro ao processar o pagamento. Tente novamente.'
            );
            return Promise.reject(error);
        });
    },

    /**
     * Get card data from form elements following payment_demo pattern
     * @private
     */
    _getCardDataFromForm: function() {
        // Use simple element IDs matching the template
        const cardHolderName = document.getElementById('card_holder_name');
        const cardNumber = document.getElementById('card_number');
        const cardExpiryMonth = document.getElementById('card_expiry_month');
        const cardExpiryYear = document.getElementById('card_expiry_year');
        const cardCvv = document.getElementById('card_cvv');

        // Log which elements are found/missing for debugging
        const missingElements = [];
        if (!cardHolderName) missingElements.push('Nome do Portador');
        if (!cardNumber) missingElements.push('Número do Cartão');
        if (!cardExpiryMonth) missingElements.push('Mês de Expiração');
        if (!cardExpiryYear) missingElements.push('Ano de Expiração');
        if (!cardCvv) missingElements.push('CVV');

        if (missingElements.length > 0) {
            const errorMsg = `Payment form elements not found: ${missingElements.join(', ')}`;
            console.error('Pagar.me:', errorMsg);
            this._displayError('Erro do Formulário', 'Campos do cartão não encontrados');
            return null;
        }

        // Validate all fields have values
        const data = {
            holderName: cardHolderName.value.trim(),
            number: cardNumber.value.replace(/\s/g, ''),
            expiryMonth: cardExpiryMonth.value,
            expiryYear: cardExpiryYear.value,
            cvv: cardCvv.value
        };

        if (!data.holderName || !data.number || !data.expiryMonth || !data.expiryYear || !data.cvv) {
            this._displayError('Dados Incompletos', 'Por favor, preencha todos os campos do cartão');
            return null;
        }

        return data;
    },

    /**
     * Prepare the inline form for Pagar.me payments following payment_demo pattern.
     *
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} code - The code of the selected payment option's provider
     * @param {integer} paymentOptionId - The id of the selected payment option
     * @param {string} flow - The online payment flow of the selected payment option
     * @return {Promise}
     */
    _prepareInlineForm: function (code, paymentOptionId, flow) {
        if (code !== 'pagarme') {
            return this._super(...arguments);
        } else if (flow === 'token') {
            return Promise.resolve();
        }

        console.log('Pagar.me: Preparing inline form');
        this._setPaymentFlow('direct');
        
        // Add input formatting after ensuring elements exist
        setTimeout(() => {
            this._setupInputFormatting();
        }, 100);
        
        return Promise.resolve();
    },

    /**
     * Setup input formatting for card fields
     * @private
     */
    _setupInputFormatting: function() {
        const cardNumber = document.getElementById('card_number');
        const cardCvv = document.getElementById('card_cvv');
        const cardHolder = document.getElementById('card_holder_name');

        if (cardNumber) {
            cardNumber.addEventListener('input', function() {
                const value = this.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
                const formattedValue = value.match(/.{1,4}/g);
                this.value = formattedValue ? formattedValue.join(' ') : '';
                if (this.value.length > 19) {
                    this.value = this.value.slice(0, 19);
                }
            });
        }

        if (cardCvv) {
            cardCvv.addEventListener('input', function() {
                this.value = this.value.replace(/[^0-9]/gi, '');
                if (this.value.length > 4) {
                    this.value = this.value.slice(0, 4);
                }
            });
        }

        if (cardHolder) {
            cardHolder.addEventListener('input', function() {
                this.value = this.value.replace(/[^a-zA-ZÀ-ÿ\s]/gi, '');
            });
        }
    },
};

checkoutForm.include(pagarmePaymentMixin);
manageForm.include(pagarmePaymentMixin);