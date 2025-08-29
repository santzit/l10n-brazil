# Copyright 2024 OCA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
import pprint

from odoo import http, _
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class PagarmeController(http.Controller):

    @http.route(
        "/payment/pagarme/process",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def pagarme_process_payment(self, **kwargs):
        """Process payment using the token from frontend."""
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("Pagar.me payment processing data: %s", pprint.pformat(data))
            
            # Get transaction
            tx_id = data.get("tx_id")
            token = data.get("token")
            
            if not tx_id or not token:
                return {"error": _("Missing transaction ID or token")}
            
            tx = request.env["payment.transaction"].sudo().browse(int(tx_id))
            if not tx or tx.provider != "pagarme":
                return {"error": _("Invalid transaction")}
            
            # Store the token
            tx.pagarme_token = token
            
            # Create order in Pagar.me
            try:
                result = tx._pagarme_create_order(data)
                return {
                    "success": True,
                    "order_id": result.get("id"),
                    "status": result.get("status"),
                }
            except Exception as e:
                _logger.error("Failed to create Pagar.me order: %s", e)
                return {"error": str(e)}
                
        except Exception as e:
            _logger.error("Error processing Pagar.me payment: %s", e)
            return {"error": _("Payment processing failed")}

    @http.route(
        "/payment/pagarme/webhook",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def pagarme_webhook(self, **kwargs):
        """Handle webhooks from Pagar.me."""
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("Pagar.me webhook received: %s", pprint.pformat(data))
            
            # Find transaction
            tx = request.env["payment.transaction"].sudo()._pagarme_form_get_tx_from_data(data)
            
            if tx:
                tx._pagarme_process_webhook_data(data)
                return {"status": "ok"}
            else:
                _logger.warning("Transaction not found for webhook data: %s", data)
                return {"status": "error", "message": "Transaction not found"}
                
        except Exception as e:
            _logger.error("Error processing Pagar.me webhook: %s", e)
            return {"status": "error", "message": str(e)}

    @http.route(
        "/payment/pagarme/return",
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
    )
    def pagarme_return(self, **kwargs):
        """Handle return from Pagar.me."""
        _logger.info("Pagar.me return with data: %s", pprint.pformat(kwargs))
        
        # Redirect to payment status page
        return request.redirect("/payment/status")

    @http.route(
        "/payment/pagarme/test_connection",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def pagarme_test_connection(self, **kwargs):
        """Test connection to Pagar.me API."""
        try:
            data = json.loads(request.httprequest.data)
            app_id = data.get("app_id")
            api_key = data.get("api_key")
            
            if not app_id or not api_key:
                return {"error": _("Missing credentials")}
            
            # Create a temporary acquirer to test connection
            acquirer = request.env["payment.acquirer"].sudo().create({
                "name": "Test Pagar.me",
                "provider": "pagarme",
                "pagarme_app_id": app_id,
                "pagarme_api_key": api_key,
                "state": "test",
            })
            
            try:
                # Test API connection
                result = acquirer._pagarme_make_request("/orders", method="GET")
                acquirer.unlink()  # Clean up test acquirer
                return {"success": True, "message": _("Connection successful")}
            except Exception as e:
                acquirer.unlink()  # Clean up test acquirer
                return {"error": str(e)}
                
        except Exception as e:
            _logger.error("Error testing Pagar.me connection: %s", e)
            return {"error": _("Connection test failed")}