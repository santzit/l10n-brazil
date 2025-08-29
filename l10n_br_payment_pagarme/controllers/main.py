# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib
import hmac
import json
import logging
import pprint

from odoo import http, _
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class PagarmeController(http.Controller):

    _return_url = "/payment/pagarme/return"
    _webhook_url = "/payment/pagarme/webhook"

    @http.route(
        "/payment/pagarme/return", type="http", auth="public", methods=["GET", "POST"], 
        csrf=False, save_session=False
    )
    def pagarme_return_from_checkout(self, **data):
        """ Process the return from Pagar.me checkout. """
        _logger.info("Handling Pagar.me return with data:\n%s", pprint.pformat(data))

        # Extract transaction reference
        tx_reference = data.get("reference")
        if not tx_reference:
            _logger.error("Missing transaction reference in return data")
            return request.redirect("/payment/process")

        # Find the transaction
        tx = request.env["payment.transaction"].sudo().search([
            ("reference", "=", tx_reference),
            ("acquirer_id.provider", "=", "pagarme")
        ], limit=1)

        if not tx:
            _logger.error("Transaction with reference %s not found", tx_reference)
            return request.redirect("/payment/process")

        try:
            # Store the card token from the frontend
            if data.get("card_token"):
                tx._pagarme_tokenize_from_feedback_data(data)
                
            # Process the payment
            tx._send_payment_request()
            
        except Exception as error:
            _logger.exception("Error processing Pagar.me return")
            tx._set_error(f"Pagar.me: {str(error)}")

        return request.redirect("/payment/process")

    @http.route(
        "/payment/pagarme/webhook", type="http", auth="public", methods=["POST"], 
        csrf=False, save_session=False
    )
    def pagarme_webhook(self):
        """ Handle Pagar.me webhook notifications. """
        data = json.loads(request.httprequest.data)
        _logger.info("Received Pagar.me webhook:\n%s", pprint.pformat(data))

        # Validate webhook signature if secret is configured
        webhook_secret = None
        
        # Try to find an acquirer with webhook secret configured
        acquirers = request.env["payment.acquirer"].sudo().search([
            ("provider", "=", "pagarme"),
            ("state", "!=", "disabled"),
            ("pagarme_webhook_secret", "!=", False)
        ])
        
        if acquirers:
            webhook_secret = acquirers[0].pagarme_webhook_secret
            
        if webhook_secret:
            signature = request.httprequest.headers.get("X-Hub-Signature-256")
            if not self._verify_webhook_signature(
                request.httprequest.data, signature, webhook_secret
            ):
                _logger.warning("Invalid webhook signature from Pagar.me")
                return "Invalid signature", 400

        # Extract charge data from webhook
        charge_data = data.get("data")
        if not charge_data:
            _logger.warning("Missing charge data in webhook")
            return "Missing charge data", 400

        charge_id = charge_data.get("id")
        if not charge_id:
            _logger.warning("Missing charge ID in webhook data")
            return "Missing charge ID", 400

        # Find transaction by charge ID
        tx = request.env["payment.transaction"].sudo().search([
            ("pagarme_charge_id", "=", charge_id)
        ], limit=1)

        if not tx:
            _logger.warning("Transaction with charge ID %s not found", charge_id)
            return "Transaction not found", 404

        try:
            # Process the webhook
            tx._process_webhook_data(charge_data)
            _logger.info("Successfully processed webhook for transaction %s", tx.reference)
            return "OK"
            
        except Exception as error:
            _logger.exception("Error processing Pagar.me webhook")
            return f"Error: {str(error)}", 500

    def _verify_webhook_signature(self, payload, signature, secret):
        """ Verify webhook signature from Pagar.me. """
        if not signature or not signature.startswith("sha256="):
            return False
            
        expected_signature = "sha256=" + hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)


class WebsiteSalePagarme(WebsiteSale):
    """ Extend WebsiteSale to handle Pagar.me specific checkout. """

    def _get_shop_payment_values(self, order, **kwargs):
        """ Add Pagar.me specific values to shop payment. """
        values = super()._get_shop_payment_values(order, **kwargs)
        
        # Add any Pagar.me specific checkout values if needed
        return values