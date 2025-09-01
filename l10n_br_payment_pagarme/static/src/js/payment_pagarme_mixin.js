odoo.define('l10n_br_payment_pagarme.payment_pagarme_mixin', function (require) {
    'use strict';

    return {

        /**
         * Simulate a feedback from a payment provider and redirect the customer to the status page.
         *
         * @private
         * @param {object} processingValues - The processing values of the transaction.
         * @return {void}
         */
        async processPagarmePayment(processingValues) {
            const customerInput = document.getElementById('customer_input').value;
            const simulatedPaymentState = document.getElementById('simulated_payment_state').value;

            // Use jQuery AJAX which is available in Odoo frontend
            $.ajax({
                url: '/payment/pagarme/simulate_payment',
                type: 'POST',
                dataType: 'json',
                data: {
                    'reference': processingValues.reference,
                    'payment_details': customerInput,
                    'simulated_state': simulatedPaymentState,
                    'csrf_token': $('input[name="csrf_token"]').val()
                },
                success: function() {
                    window.location = '/payment/status';
                },
                error: function(xhr, status, error) {
                    alert("Payment processing failed: " + (xhr.responseJSON?.error || error));
                }
            });
        },

    };
});