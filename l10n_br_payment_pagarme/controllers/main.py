# Copyright 2024 OCA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging

import requests
from requests.auth import HTTPBasicAuth

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

            # Process the payment by calling Pagar.me API directly
            result = self._process_pagarme_payment(transaction)
            
            if result.get("success"):
                _logger.info(
                    "Pagar.me: Payment processing completed for transaction %s", reference
                )
                return {"success": True}
            else:
                _logger.error(
                    "Pagar.me: Payment processing failed for transaction %s: %s", 
                    reference, result.get("error", "Unknown error")
                )
                return {"error": result.get("error", "Payment processing failed")}

        except Exception as e:
            _logger.error(
                "Pagar.me: Payment processing error: %s", str(e), exc_info=True
            )
            return {"error": f"Payment processing failed: {str(e)}"}

    def _process_pagarme_payment(self, transaction):
        """Process payment by calling Pagar.me API directly."""
        _logger.info(
            "Pagar.me: Starting payment request for transaction %s", transaction.reference
        )

        # Prepare order data for Pagar.me Order API
        order_data = {
            "amount": int(transaction.amount * 100),  # Convert to cents
            "currency": "BRL",  # Brazilian Real
            "items": [
                {
                    "amount": int(transaction.amount * 100),
                    "description": f"Payment for order {transaction.reference}",
                    "quantity": 1,
                    "code": transaction.reference,
                }
            ],
            "payments": [
                {
                    "payment_method": "credit_card",
                    "amount": int(transaction.amount * 100),
                    "credit_card": {
                        "card_token": transaction.pagarme_token,
                        "installments": 1,
                        "capture": True,
                    },
                }
            ],
            "customer": {
                "name": transaction.partner_name or "",
                "email": transaction.partner_email or "",
                "type": "individual",
                "country": "BR",
                "documents": [
                    {
                        "type": "cpf",
                        "number": "00000000000",  # This should be obtained from partner
                    }
                ],
            },
            "metadata": {
                "odoo_reference": transaction.reference,
                "odoo_transaction_id": str(transaction.id),
            },
        }

        # Prepare headers and authentication
        # Pagar.me uses Basic Authentication with secret key as username
        # and empty password
        auth = HTTPBasicAuth(transaction.provider_id.pagarme_api_key, "")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Odoo-Pagar.me/1.0",
        }

        # Log request (mask sensitive data)
        _logger.info(
            "Pagar.me: API Request URL: %s", "https://api.pagar.me/core/v5/orders"
        )
        _logger.info(
            "Pagar.me: API Request Headers: %s",
            json.dumps({k: v for k, v in headers.items()}),
        )
        _logger.info("Pagar.me: Using Basic Auth with API key")
        _logger.info(
            "Pagar.me: API Request Payload: %s",
            json.dumps(
                {
                    **order_data,
                    "payments": [
                        {
                            **payment,
                            "credit_card": {
                                **payment["credit_card"],
                                "card_token": "***MASKED***",
                            },
                        }
                        for payment in order_data["payments"]
                    ],
                }
            ),
        )

        try:
            # Make API request to Pagar.me Orders endpoint
            response = requests.post(
                "https://api.pagar.me/core/v5/orders",
                json=order_data,
                auth=auth,
                headers=headers,
                timeout=30,
            )

            # Log response
            _logger.info("Pagar.me: API Response Status: %s", response.status_code)
            _logger.info("Pagar.me: API Response Headers: %s", dict(response.headers))

            if response.status_code == 200:
                result = response.json()
                _logger.info("Pagar.me: API Response Data: %s", json.dumps(result))

                # Update transaction with response data
                transaction.provider_reference = result.get("id")

                # Get payment status from the charges array
                charges = result.get("charges", [])
                if charges:
                    charge_status = charges[0].get("status")
                    _logger.info("Pagar.me: Charge status: %s", charge_status)

                    # Map Pagar.me charge status to Odoo transaction states
                    if charge_status == "paid":
                        # Check if manual capture is enabled like payment_demo
                        if transaction.provider_id.capture_manually:
                            transaction._set_authorized()
                            _logger.info(
                                "Pagar.me: Transaction %s marked as authorized",
                                transaction.reference,
                            )
                        else:
                            transaction._set_done()
                            _logger.info(
                                "Pagar.me: Transaction %s marked as done",
                                transaction.reference,
                            )
                    elif charge_status in ["pending", "processing"]:
                        transaction._set_pending()
                        _logger.info(
                            "Pagar.me: Transaction %s marked as pending", transaction.reference
                        )
                    elif charge_status in ["failed", "canceled"]:
                        error_message = (
                            charges[0]
                            .get("last_transaction", {})
                            .get("gateway_response", {})
                            .get("reason", "Payment failed")
                        )
                        transaction._set_error(error_message)
                        _logger.error(
                            "Pagar.me: Transaction %s failed: %s",
                            transaction.reference,
                            error_message,
                        )
                        return {"success": False, "error": error_message}
                    else:
                        transaction._set_pending()
                        _logger.warning(
                            "Pagar.me: Unknown charge status %s for transaction %s",
                            charge_status,
                            transaction.reference,
                        )
                else:
                    # No charges found, set as pending and wait for webhook
                    transaction._set_pending()
                    _logger.warning(
                        "Pagar.me: No charges found for transaction %s", transaction.reference
                    )

                return {"success": True}

            else:
                error_data = response.text
                try:
                    error_json = response.json()
                    error_message = error_json.get("message", error_data)
                    _logger.error(
                        "Pagar.me: API Error Response: %s", json.dumps(error_json)
                    )
                except Exception:
                    error_message = error_data
                    _logger.error("Pagar.me: API Error Response (raw): %s", error_data)

                transaction._set_error(error_message)
                return {"success": False, "error": error_message}

        except requests.exceptions.Timeout:
            error_msg = "Request timeout - Pagar.me API não respondeu"
            _logger.error("Pagar.me: %s for transaction %s", error_msg, transaction.reference)
            transaction._set_error(error_msg)
            return {"success": False, "error": error_msg}
        except requests.exceptions.ConnectionError:
            error_msg = "Connection error - Não foi possível conectar à API do Pagar.me"
            _logger.error("Pagar.me: %s for transaction %s", error_msg, transaction.reference)
            transaction._set_error(error_msg)
            return {"success": False, "error": error_msg}
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error {e.response.status_code}"
            _logger.error("Pagar.me: %s for transaction %s", error_msg, transaction.reference)
            transaction._set_error(error_msg)
            return {"success": False, "error": error_msg}
        except requests.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            _logger.error("Pagar.me: %s for transaction %s", error_msg, transaction.reference)
            transaction._set_error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            _logger.error("Pagar.me: %s for transaction %s", error_msg, transaction.reference)
            transaction._set_error(error_msg)
            return {"success": False, "error": error_msg}

    @http.route(_webhook_url, type="json", auth="public", methods=["POST"], csrf=False)
    def pagarme_webhook(self, **data):
        """Handle webhook notifications from Pagar.me."""
        try:
            _logger.info("Pagar.me: Received webhook notification")
            _logger.info("Pagar.me: Webhook data: %s", json.dumps(data))

            # Process the notification using the standard payment framework method
            request.env["payment.transaction"].sudo()._handle_notification_data(
                "pagarme", data
            )

            _logger.info("Pagar.me: Webhook processed successfully")
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
