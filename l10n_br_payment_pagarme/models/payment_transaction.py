# Copyright 2024 OCA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging

import requests
from requests.auth import HTTPBasicAuth

from odoo import fields, models

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    pagarme_token = fields.Char(
        string="Pagar.me Token",
        help="Token received from Pagar.me tokenization",
        readonly=True,
    )

    def _get_specific_processing_values(self, processing_values):
        """Return Pagar.me-specific processing values."""
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != "pagarme":
            return res

        # Return specific keys expected by the payment framework, similar to demo
        return {
            "public_key": self.provider_id.pagarme_app_id,
            "api_key": self.provider_id.pagarme_api_key,
            "amount": int(self.amount * 100),  # Convert to cents for Pagar.me API
            "currency": self.currency_id.name.lower(),
        }

    def _send_payment_request(self):
        """Send payment request to Pagar.me using Order API."""
        if self.provider_code != "pagarme":
            return super()._send_payment_request()

        # For inline payment, we need a token from the frontend
        if not self.pagarme_token:
            # This should not happen in normal flow as JS should provide token
            _logger.error(
                "Pagar.me: No token provided for transaction %s", self.reference
            )
            self._set_error("Token de cartão não fornecido")
            return

        _logger.info(
            "Pagar.me: Starting payment request for transaction %s", self.reference
        )

        # Prepare order data for Pagar.me Order API
        order_data = {
            "amount": int(self.amount * 100),  # Convert to cents
            "currency": "BRL",  # Brazilian Real
            "items": [
                {
                    "amount": int(self.amount * 100),
                    "description": f"Payment for order {self.reference}",
                    "quantity": 1,
                    "code": self.reference,
                }
            ],
            "payments": [
                {
                    "payment_method": "credit_card",
                    "amount": int(self.amount * 100),
                    "credit_card": {
                        "card_token": self.pagarme_token,
                        "installments": 1,
                        "capture": True,
                    },
                }
            ],
            "customer": {
                "name": self.partner_name or "",
                "email": self.partner_email or "",
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
                "odoo_reference": self.reference,
                "odoo_transaction_id": str(self.id),
            },
        }

        # Prepare headers and authentication
        # Pagar.me uses Basic Authentication with secret key as username
        # and empty password
        auth = HTTPBasicAuth(self.provider_id.pagarme_api_key, "")
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
                self.provider_reference = result.get("id")

                # Get payment status from the charges array
                charges = result.get("charges", [])
                if charges:
                    charge_status = charges[0].get("status")
                    _logger.info("Pagar.me: Charge status: %s", charge_status)

                    # Map Pagar.me charge status to Odoo transaction states
                    if charge_status == "paid":
                        self._set_done()
                        _logger.info(
                            "Pagar.me: Transaction %s marked as done", self.reference
                        )
                    elif charge_status in ["pending", "processing"]:
                        self._set_pending()
                        _logger.info(
                            "Pagar.me: Transaction %s marked as pending", self.reference
                        )
                    elif charge_status in ["failed", "canceled"]:
                        error_message = (
                            charges[0]
                            .get("last_transaction", {})
                            .get("gateway_response", {})
                            .get("reason", "Payment failed")
                        )
                        self._set_error(f"Payment failed: {error_message}")
                        _logger.error(
                            "Pagar.me: Transaction %s failed: %s",
                            self.reference,
                            error_message,
                        )
                    else:
                        self._set_pending()
                        _logger.warning(
                            "Pagar.me: Unknown charge status %s for transaction %s",
                            charge_status,
                            self.reference,
                        )
                else:
                    # No charges found, set as pending and wait for webhook
                    self._set_pending()
                    _logger.warning(
                        "Pagar.me: No charges found for transaction %s", self.reference
                    )

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

                response.raise_for_status()

        except requests.exceptions.Timeout:
            error_msg = "Request timeout - Pagar.me API não respondeu"
            _logger.error("Pagar.me: %s for transaction %s", error_msg, self.reference)
            self._set_error(error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = "Connection error - Não foi possível conectar à API do Pagar.me"
            _logger.error("Pagar.me: %s for transaction %s", error_msg, self.reference)
            self._set_error(error_msg)
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error {e.response.status_code}"
            _logger.error("Pagar.me: %s for transaction %s", error_msg, self.reference)
            self._set_error(error_msg)
        except requests.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            _logger.error("Pagar.me: %s for transaction %s", error_msg, self.reference)
            self._set_error(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            _logger.error("Pagar.me: %s for transaction %s", error_msg, self.reference)
            self._set_error(error_msg)

    def _process_notification_data(self, notification_data):
        """Process notification data from Pagar.me webhooks."""
        if self.provider_code != "pagarme":
            return super()._process_notification_data(notification_data)

        _logger.info(
            "Pagar.me: Processing webhook notification for transaction %s",
            self.reference,
        )
        _logger.info("Pagar.me: Webhook data: %s", json.dumps(notification_data))

        # Handle both webhook format and direct order data format
        event_type = notification_data.get("type")
        if event_type:
            # Webhook format with event type
            event_data = notification_data.get("data", {})
            
            if event_type == "order.paid":
                self._set_done()
                _logger.info(
                    "Pagar.me: Transaction %s marked as done via webhook",
                    self.reference
                )
            elif event_type == "order.payment_failed":
                error_message = event_data.get("reason", "Payment failed")
                self._set_error(f"Payment failed: {error_message}")
                _logger.error(
                    "Pagar.me: Transaction %s failed via webhook: %s",
                    self.reference,
                    error_message,
                )
            elif event_type == "order.canceled":
                self._set_canceled()
                _logger.info(
                    "Pagar.me: Transaction %s marked as canceled via webhook",
                    self.reference
                )
            elif event_type in ["order.pending", "order.processing"]:
                self._set_pending()
                _logger.info(
                    "Pagar.me: Transaction %s marked as pending via webhook",
                    self.reference
                )
            else:
                _logger.warning(
                    "Pagar.me: Unknown webhook event type %s for transaction %s",
                    event_type,
                    self.reference,
                )
        else:
            # Direct order data format (for tests and direct API responses)
            order_status = notification_data.get("status")
            charges = notification_data.get("charges", [])
            
            paid_status = (order_status == "paid" or 
                          (charges and charges[0].get("status") == "paid"))
            if paid_status:
                self._set_done()
                _logger.info(
                    "Pagar.me: Transaction %s marked as done", self.reference
                )
            elif (order_status == "failed" or 
                  (charges and charges[0].get("status") == "failed")):
                error_message = "Payment failed"
                if charges:
                    error_message = (
                        charges[0]
                        .get("last_transaction", {})
                        .get("gateway_response", {})
                        .get("reason", error_message)
                    )
                self._set_error(f"Payment failed: {error_message}")
                _logger.error(
                    "Pagar.me: Transaction %s failed: %s",
                    self.reference,
                    error_message,
                )
            elif (order_status == "canceled" or 
                  (charges and charges[0].get("status") == "canceled")):
                self._set_canceled()
                _logger.info(
                    "Pagar.me: Transaction %s marked as canceled", self.reference
                )
            elif (order_status in ["pending", "processing"] or 
                  (charges and charges[0].get("status") in ["pending", "processing"])):
                self._set_pending()
                _logger.info(
                    "Pagar.me: Transaction %s marked as pending", self.reference
                )
            else:
                _logger.warning(
                    "Pagar.me: Unknown order status %s for transaction %s",
                    order_status,
                    self.reference,
                )
