# Copyright 2024 OCA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import pprint

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PagarmeController(http.Controller):
    _webhook_url = "/payment/pagarme/webhook"
    _return_url = "/payment/pagarme/return"

    @http.route(_return_url, type="http", auth="public", methods=["GET"], csrf=False)
    def pagarme_return(self, **kwargs):
        """Handle return from Pagar.me checkout."""
        try:
            reference = kwargs.get("reference")
            status = kwargs.get("status", "cancel")
            
            _logger.info(
                "Pagar.me return with reference: %s, status: %s", reference, status
            )

            if not reference:
                _logger.error("Missing reference in Pagar.me return")
                return request.redirect("/payment/status")

            # Find the transaction
            transaction = (
                request.env["payment.transaction"]
                .sudo()
                .search([("reference", "=", reference)], limit=1)
            )

            if not transaction:
                _logger.error("Transaction not found for reference: %s", reference)
                return request.redirect("/payment/status")

            # Handle different statuses
            if status == "success":
                # Payment completed - wait for webhook confirmation
                _logger.info("Payment success for transaction %s", reference)
            elif status == "cancel":
                # Payment canceled by user
                transaction._set_canceled()
                _logger.info("Payment canceled for transaction %s", reference)
            else:
                _logger.warning(
                    "Unknown status '%s' for transaction %s", status, reference
                )

            return request.redirect("/payment/status")

        except Exception as e:
            _logger.error("Pagar.me return error: %s", str(e))
            return request.redirect("/payment/status")

    @http.route(_webhook_url, type="json", auth="public", methods=["POST"], csrf=False)
    def pagarme_webhook(self, **kwargs):
        """Handle webhook notifications from Pagar.me."""
        try:
            data = request.jsonrequest or {}
            _logger.info("Pagar.me webhook received: %s", pprint.pformat(data))

            # Find transaction using the notification data
            tx = (
                request.env["payment.transaction"]
                .sudo()
                ._get_tx_from_notification_data("pagarme", data)
            )

            if not tx:
                _logger.error("No transaction found for Pagar.me webhook: %s", data)
                return {"error": "Transaction not found"}

            # Process the notification
            tx._process_notification_data(data)
            _logger.info("Processed webhook for transaction %s", tx.reference)

            return {"status": "received"}

        except Exception as e:
            _logger.error("Pagar.me webhook error: %s", str(e))
            return {"error": str(e)}
