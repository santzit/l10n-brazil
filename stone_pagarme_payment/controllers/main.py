# Copyright 2024 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
import pprint

from odoo import http, _
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class StonePagarmeController(http.Controller):

    @http.route(
        "/payment/stone_pagarme/return",
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
        save_session=False,
    )
    def stone_pagarme_return_from_checkout(self, **post):
        """Handle return from Stone/Pagar.me checkout."""
        _logger.info("Stone/Pagar.me: handling return from checkout with data:\n%s", pprint.pformat(post))
        
        # Handle the return data and redirect appropriately
        reference = post.get("reference")
        if not reference:
            _logger.error("Stone/Pagar.me: missing reference in return data")
            return request.redirect("/payment/process")
            
        # Find the transaction
        tx_sudo = request.env["payment.transaction"].sudo().search([
            ("reference", "=", reference),
            ("provider_code", "=", "stone_pagarme"),
        ])
        
        if not tx_sudo:
            _logger.error("Stone/Pagar.me: no transaction found for reference %s", reference)
            return request.redirect("/payment/process")
            
        # Process the return data
        try:
            tx_sudo._handle_notification_data("stone_pagarme", post)
        except ValidationError as e:
            _logger.error("Stone/Pagar.me: validation error processing return data: %s", e)
            
        return request.redirect("/payment/status")

    @http.route(
        "/payment/stone_pagarme/webhook", 
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def stone_pagarme_webhook(self, **kwargs):
        """Handle Stone/Pagar.me webhook notifications."""
        data = json.loads(request.httprequest.data.decode())
        _logger.info("Stone/Pagar.me: webhook received with data:\n%s", pprint.pformat(data))
        
        try:
            # Validate webhook data structure
            if "data" not in data:
                _logger.error("Stone/Pagar.me: invalid webhook data structure")
                return {"status": "error", "message": "Invalid data structure"}
                
            webhook_data = data["data"]
            
            # Find the transaction based on metadata
            metadata = webhook_data.get("metadata", {})
            reference = metadata.get("odoo_reference")
            
            if not reference:
                _logger.error("Stone/Pagar.me: missing odoo_reference in webhook metadata")
                return {"status": "error", "message": "Missing reference"}
                
            # Find and update the transaction
            tx_sudo = request.env["payment.transaction"].sudo().search([
                ("reference", "=", reference),
                ("provider_code", "=", "stone_pagarme"),
            ])
            
            if not tx_sudo:
                _logger.error("Stone/Pagar.me: no transaction found for reference %s", reference)
                return {"status": "error", "message": "Transaction not found"}
                
            # Process the webhook data
            tx_sudo._handle_notification_data("stone_pagarme", webhook_data)
            
            return {"status": "success"}
            
        except Exception as e:
            _logger.error("Stone/Pagar.me: error processing webhook: %s", e)
            return {"status": "error", "message": str(e)}

    @http.route(
        "/payment/stone_pagarme/process_payment",
        type="json", 
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def stone_pagarme_process_payment(self, **kwargs):
        """Process transparent payment with Stone/Pagar.me."""
        _logger.info("Stone/Pagar.me: processing transparent payment")
        
        try:
            # Get transaction reference
            reference = kwargs.get("reference")
            if not reference:
                return {"status": "error", "message": "Missing transaction reference"}
                
            # Find the transaction
            tx_sudo = request.env["payment.transaction"].sudo().search([
                ("reference", "=", reference),
                ("provider_code", "=", "stone_pagarme"),
            ])
            
            if not tx_sudo:
                return {"status": "error", "message": "Transaction not found"}
                
            # Get card data from request
            card_data = {
                "card_number": kwargs.get("card_number"),
                "card_holder_name": kwargs.get("card_holder_name"),
                "card_expiration_date": kwargs.get("card_expiration_date"),
                "card_cvv": kwargs.get("card_cvv"),
                "installments": kwargs.get("installments", 1),
            }
            
            # Validate card data
            if not all([
                card_data["card_number"],
                card_data["card_holder_name"], 
                card_data["card_expiration_date"],
                card_data["card_cvv"],
            ]):
                return {"status": "error", "message": "Missing card information"}
                
            # Prepare transaction data
            transaction_data = tx_sudo._stone_pagarme_create_transaction_request(card_data)
            
            # Make request to Stone/Pagar.me API
            response = tx_sudo.provider_id._stone_pagarme_make_request("orders", transaction_data)
            
            # Process the response
            tx_sudo._stone_pagarme_process_transaction_response(response)
            
            return {
                "status": "success",
                "transaction_id": tx_sudo.stone_pagarme_transaction_id,
                "redirect_url": "/payment/status",
            }
            
        except Exception as e:
            _logger.error("Stone/Pagar.me: error processing payment: %s", e)
            return {"status": "error", "message": str(e)}