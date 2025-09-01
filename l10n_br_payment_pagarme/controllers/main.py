# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class PaymentPagarmeController(http.Controller):
    _simulation_url = '/payment/pagarme/simulate_payment'
    _process_url = '/payment/pagarme/process'

    @http.route(_simulation_url, type='json', auth='public')
    def pagarme_simulate_payment(self, **data):
        """ Simulate the response of a payment request.

        :param dict data: The simulated notification data.
        :return: None
        """
        request.env['payment.transaction'].sudo()._handle_notification_data(
            'pagarme', data
        )

    @http.route(_process_url, type='http', auth='public', methods=['POST'], csrf=False)
    def pagarme_process_payment(self, **data):
        """ Process payment form submission.

        :param dict data: The form data.
        :return: Redirect to payment status page
        """
        # This route exists to provide a valid form action
        # The actual processing is handled by JavaScript
        return request.redirect('/payment/status')