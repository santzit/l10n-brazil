# Copyright 2024 OCA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PagarmeController(http.Controller):
    _webhook_url = "/payment/pagarme/webhook"
    _payment_url = "/payment/pagarme/payment"

    @http.route(_payment_url, type="json", auth="public", methods=["POST"], csrf=False)
    def pagarme_payment(self, **kwargs):
        """Handle payment processing request from frontend."""
        try:
            # Get transaction reference
            reference = kwargs.get("reference")
            if not reference:
                return {"error": "Missing transaction reference"}

            # Find the transaction
            transaction = (
                request.env["payment.transaction"]
                .sudo()
                .search([("reference", "=", reference)], limit=1)
            )

            if not transaction:
                return {"error": "Transaction not found"}

            # Store card data temporarily (in a real implementation,
            # this would be tokenized)
            transaction.pagarme_token = "test_token_" + reference

            # Process the payment
            transaction._send_payment_request()

            return {"success": True}

        except Exception as e:
            _logger.error("Pagar.me payment error: %s", str(e))
            return {"error": str(e)}

    @http.route(_webhook_url, type="json", auth="public", methods=["POST"], csrf=False)
    def pagarme_webhook(self, **kwargs):
        """Handle webhook notifications from Pagar.me."""
        try:
            data = kwargs or {}

            # Find transaction by Pagar.me ID
            provider_reference = data.get("id")
            if not provider_reference:
                return {"error": "Missing provider reference"}

            transaction = (
                request.env["payment.transaction"]
                .sudo()
                .search([("provider_reference", "=", provider_reference)], limit=1)
            )

            if not transaction:
                return {"error": "Transaction not found"}

            # Process the notification
            transaction._process_notification_data(data)

            return {"status": "received"}

        except Exception as e:
            _logger.error("Pagar.me webhook error: %s", str(e))
            return {"error": str(e)}
