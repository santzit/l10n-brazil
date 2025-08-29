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

    def _create_pagarme_checkout_session(self, transaction):
        """Create a checkout session with Pagar.me API."""
        self.ensure_one()
        
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
                    }
                }
            ],
            "metadata": {
                "odoo_reference": transaction.reference,
                "transaction_id": transaction.id,
            }
        }

        # Make API request to Pagar.me
        headers = {
            "Authorization": f"Bearer {self.pagarme_api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                "https://api.pagar.me/core/v5/orders",
                json=order_data,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()

            # Extract checkout URL
            checkout_url = result.get("checkout", {}).get("url")
            if not checkout_url:
                raise ValidationError("Pagar.me did not return a checkout URL")

            # Store the order ID for later reference
            transaction.provider_reference = result.get("id")
            
            return checkout_url

        except requests.RequestException as e:
            _logger.error("Pagar.me checkout session creation failed: %s", e)
            raise ValidationError(f"Failed to create checkout session: {str(e)}") from e
        except Exception as e:
            _logger.error("Unexpected error creating Pagar.me checkout: %s", e)
            raise ValidationError(f"Checkout creation error: {str(e)}") from e
