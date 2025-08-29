# Copyright 2024 OCA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PagarmeController(http.Controller):
    _webhook_url = "/payment/pagarme/webhook"
    _payment_url = "/payment/pagarme/payment"

    @http.route(_payment_url, type="json", auth="public", methods=["POST"], csrf=False)
    def pagarme_payment(self, **kwargs):
        """Handle payment processing request from frontend with tokenized card data."""
        try:
            _logger.info(
                "Pagar.me: Received payment request with parameters: %s",
                json.dumps(
                    {
                        k: "***MASKED***" if "token" in k.lower() else v
                        for k, v in kwargs.items()
                    }
                ),
            )

            # Get transaction reference
            reference = kwargs.get("reference")
            if not reference:
                _logger.error(
                    "Pagar.me: Missing transaction reference in payment request"
                )
                return {"error": "Missing transaction reference"}

            # Find the transaction
            transaction = (
                request.env["payment.transaction"]
                .sudo()
                .search([("reference", "=", reference)], limit=1)
            )

            if not transaction:
                _logger.error(
                    "Pagar.me: Transaction not found for reference: %s", reference
                )
                return {"error": "Transaction not found"}

            # Validate required tokenized data
            card_token = kwargs.get("card_token")
            if not card_token:
                _logger.error(
                    "Pagar.me: Missing card token in payment request for "
                    "transaction %s",
                    reference,
                )
                return {"error": "Missing card token"}

            # Store tokenized card data
            transaction.pagarme_token = card_token
            _logger.info("Pagar.me: Stored card token for transaction %s", reference)

            # Process the payment using the Order API
            transaction._send_payment_request()

            _logger.info(
                "Pagar.me: Payment processing completed for transaction %s", reference
            )
            return {"success": True}

        except Exception as e:
            _logger.error(
                "Pagar.me: Payment processing error: %s", str(e), exc_info=True
            )
            return {"error": f"Payment processing failed: {str(e)}"}

    @http.route(_webhook_url, type="json", auth="public", methods=["POST"], csrf=False)
    def pagarme_webhook(self, **kwargs):
        """Handle webhook notifications from Pagar.me."""
        try:
            _logger.info("Pagar.me: Received webhook notification")
            data = kwargs or {}
            _logger.info("Pagar.me: Webhook data: %s", json.dumps(data))

            # Extract order ID from webhook data
            event_data = data.get("data", {})
            order_id = event_data.get("id") or data.get("id")

            if not order_id:
                _logger.error("Pagar.me: Missing order ID in webhook notification")
                return {"error": "Missing order ID"}

            # Find transaction by Pagar.me order ID
            transaction = (
                request.env["payment.transaction"]
                .sudo()
                .search([("provider_reference", "=", order_id)], limit=1)
            )

            if not transaction:
                _logger.error(
                    "Pagar.me: Transaction not found for order ID: %s", order_id
                )
                return {"error": "Transaction not found"}

            _logger.info(
                "Pagar.me: Processing webhook for transaction %s", transaction.reference
            )

            # Process the notification
            transaction._process_notification_data(data)

            _logger.info(
                "Pagar.me: Webhook processed successfully for transaction %s",
                transaction.reference,
            )
            return {"status": "received"}

        except Exception as e:
            _logger.error(
                "Pagar.me: Webhook processing error: %s", str(e), exc_info=True
            )
            return {"error": f"Webhook processing failed: {str(e)}"}

    @http.route("/payment/pagarme/test", type="http", auth="public", methods=["GET"])
    def pagarme_test_connection(self, **kwargs):
        """Test endpoint for verifying Pagar.me connectivity."""
        try:
            _logger.info("Pagar.me: Test connection endpoint accessed")

            # Basic connectivity test
            import requests

            response = requests.get("https://api.pagar.me", timeout=10)
            _logger.info(
                "Pagar.me: Test connection - API responded with status %s",
                response.status_code,
            )

            return request.make_response(
                f"Pagar.me API connectivity test - Status: {response.status_code}",
                headers=[("Content-Type", "text/plain")],
            )

        except Exception as e:
            _logger.error("Pagar.me: Test connection failed: %s", str(e))
            return request.make_response(
                f"Pagar.me API connectivity test failed: {str(e)}",
                headers=[("Content-Type", "text/plain")],
                status=500,
            )
