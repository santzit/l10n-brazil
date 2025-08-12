odoo.define('payment_pagarme.payment_form', function (require) {
    const publicWidget = require('web.public.widget');
    const paymentForm = require('payment.payment_form');

    paymentForm.include({
        _processPaymentProvider: function (providerId) {
            if (this.providerSelection !== 'pagarme') {
                return this._super.apply(this, arguments);
            }

            const self = this;

            const encryptionKey = this.$('input[name="pagarme_encryption_key"]').val();

            const card = {
                card_number: this.$('input[name="card_number"]').val(),
                card_holder_name: this.$('input[name="card_name"]').val(),
                card_expiration_date: this.$('input[name="card_expiration"]').val(), // MMYY
                card_cvv: this.$('input[name="card_cvv"]').val(),
            };

            return pagarme.client.connect({ encryption_key: encryptionKey })
                .then(client => client.security.encrypt(card))
                .then(card_hash => {
                    self.$('input[name="pagarme_card_token"]').val(card_hash);
                    return self._super.apply(self, arguments);
                })
                .catch(function (error) {
                    console.error('Pagar.me encryption failed:', error);
                    self._displayError("Payment error: Could not tokenize card.");
                });
        }
    });
});
