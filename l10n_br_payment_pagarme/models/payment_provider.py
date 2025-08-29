# Copyright 2024 OCA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

import requests

from odoo import fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("pagarme", "Pagar.me")], ondelete={"pagarme": "set default"}
    )
    pagarme_app_id = fields.Char(
        string="App ID",
        help="Pagar.me Application ID",
        groups="base.group_system",
    )
    pagarme_api_key = fields.Char(
        string="API Key",
        help="Pagar.me API Key for server-side operations",
        groups="base.group_system",
    )

    def _get_pagarme_webhook_url(self):
        """Get the webhook URL for Pagar.me notifications."""
        self.ensure_one()
        base_url = self.get_base_url()
        return f"{base_url}/payment/pagarme/webhook"

    def _get_return_url(self, reference):
        """Get the return URL for payment success/cancel."""
        self.ensure_one()
        base_url = self.get_base_url()
        return f"{base_url}/payment/pagarme/return?reference={reference}"

    def _get_default_payment_method_codes(self):
        """Return the default payment method codes."""
        default_codes = super()._get_default_payment_method_codes()
        if self.code == "pagarme":
            default_codes.append("card")
        return default_codes

    def test_pagarme_connection(self):
        """Test connection to Pagar.me API for debugging purposes."""
        self.ensure_one()

        if not self.pagarme_api_key:
            raise ValidationError("Pagar.me API key is not configured")

        try:
            # Test basic connectivity with a simple GET request
            response = requests.get(
                "https://api.pagar.me/core/v5/orders",
                headers={
                    "Authorization": f"Bearer {self.pagarme_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            _logger.info(
                "Pagar.me API connection test - Status: %s", response.status_code
            )

            # Show success message to user
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Connection Test",
                    "message": (
                        f"Pagar.me API connection successful "
                        f"(HTTP {response.status_code})"
                    ),
                    "type": "success",
                },
            }
        except requests.exceptions.ConnectionError as e:
            _logger.error("Pagar.me API connection test failed: %s", e)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Connection Test Failed",
                    "message": f"Cannot connect to Pagar.me API: {str(e)}",
                    "type": "danger",
                },
            }
        except Exception as e:
            _logger.error("Pagar.me API test error: %s", e)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Connection Test Error",
                    "message": f"API test failed: {str(e)}",
                    "type": "warning",
                },
            }

    def _create_pagarme_checkout_session(self, transaction):
        """Create a checkout session with Pagar.me API."""
        self.ensure_one()

        # Validate required configuration
        if not self.pagarme_api_key:
            _logger.error("Pagar.me API key not configured for provider %s", self.name)
            raise ValidationError("Pagar.me API key is not configured")

        # Prepare order data for Pagar.me checkout API
        order_data = {
            "items": [
                {
                    "amount": int(transaction.amount * 100),  # Convert to cents
                    "description": transaction.reference or "Payment",
                    "quantity": 1,
                    "code": transaction.reference,
                }
            ],
            "customer": {
                "name": transaction.partner_name or "",
                "email": transaction.partner_email or "",
                "type": "individual",
            },
            "payments": [
                {
                    "payment_method": "checkout",
                    "checkout": {
                        "expires_in": 3600,  # 1 hour
                        "default_payment_method": "credit_card",
                        "accepted_payment_methods": ["credit_card", "boleto", "pix"],
                        "success_url": (
                            f"{self._get_return_url(transaction.reference)}"
                            "&status=success"
                        ),
                        "cancel_url": (
                            f"{self._get_return_url(transaction.reference)}"
                            "&status=cancel"
                        ),
                    },
                }
            ],
            "metadata": {
                "odoo_reference": transaction.reference,
                "transaction_id": transaction.id,
            },
        }

        # Make API request to Pagar.me
        headers = {
            "Authorization": f"Bearer {self.pagarme_api_key}",
            "Content-Type": "application/json",
        }

        # Log the request details (excluding sensitive data)
        _logger.info(
            "Creating Pagar.me checkout session for transaction %s",
            transaction.reference,
        )
        _logger.info("Request URL: https://api.pagar.me/core/v5/orders")
        _logger.info(
            "Request headers (auth masked): %s",
            {"Authorization": "Bearer ***", "Content-Type": headers["Content-Type"]},
        )
        _logger.info("Request payload: %s", order_data)

        try:
            response = requests.post(
                "https://api.pagar.me/core/v5/orders",
                json=order_data,
                headers=headers,
                timeout=30,
            )

            # Log response details
            _logger.info("Pagar.me API response status: %s", response.status_code)
            _logger.info("Pagar.me API response headers: %s", dict(response.headers))

            if response.status_code >= 400:
                error_text = response.text
                _logger.error("Pagar.me API error response: %s", error_text)

            response.raise_for_status()
            result = response.json()

            # Log successful response (excluding sensitive data)
            _logger.info("Pagar.me API successful response received")
            _logger.info("Response data: %s", result)

            # Extract checkout URL
            checkout_url = result.get("checkout", {}).get("url")
            if not checkout_url:
                _logger.error("No checkout URL in Pagar.me response: %s", result)
                raise ValidationError("Pagar.me did not return a checkout URL")

            # Store the order ID for later reference
            order_id = result.get("id")
            if order_id:
                transaction.provider_reference = order_id
                _logger.info(
                    "Stored Pagar.me order ID %s for transaction %s",
                    order_id,
                    transaction.reference,
                )
            else:
                _logger.warning("No order ID in Pagar.me response: %s", result)

            _logger.info("Checkout URL generated successfully: %s", checkout_url)
            return checkout_url

        except requests.exceptions.ConnectionError as e:
            _logger.error("Network connection error to Pagar.me API: %s", e)
            # Check if this is a sandbox/test environment issue
            if "Temporary failure in name resolution" in str(
                e
            ) or "Max retries exceeded" in str(e):
                raise ValidationError(
                    "Unable to connect to Pagar.me payment service. "
                    "This may be due to network restrictions in test environments. "
                    "Please ensure:\n"
                    "1. Your server has internet access\n"
                    "2. Pagar.me API (api.pagar.me) is accessible\n"
                    "3. Your API key is correctly configured\n"
                    "4. You are not in a restricted sandbox environment"
                ) from e
            else:
                raise ValidationError(
                    f"Unable to connect to Pagar.me payment service: {str(e)}"
                ) from e
        except requests.exceptions.Timeout as e:
            _logger.error("Timeout error calling Pagar.me API: %s", e)
            raise ValidationError(
                "Pagar.me payment service is taking too long to respond. "
                "Please try again later."
            ) from e
        except requests.exceptions.HTTPError as e:
            _logger.error("HTTP error from Pagar.me API: %s", e)
            error_msg = f"Pagar.me payment service error: {e.response.status_code}"
            if hasattr(e.response, "text"):
                error_msg += f" - {e.response.text}"
            raise ValidationError(error_msg) from e
        except requests.RequestException as e:
            _logger.error("Request exception calling Pagar.me API: %s", e)
            raise ValidationError(f"Failed to create checkout session: {str(e)}") from e
        except Exception as e:
            _logger.error("Unexpected error creating Pagar.me checkout: %s", e)
            raise ValidationError(f"Checkout creation error: {str(e)}") from e
