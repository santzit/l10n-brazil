# Copyright 2024 OCA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import requests

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
        if self.provider != "pagarme":
            return res

        pagarme_values = {
            "app_id": self.acquirer_id.pagarme_app_id,
            "amount": int(self.amount * 100),  # Convert to cents
            "currency": self.currency_id.name,
        }
        res.update(pagarme_values)
        return res

    def _send_payment_request(self):
        """Send payment request to Pagar.me."""
        if self.provider != "pagarme":
            return super()._send_payment_request()

        # Prepare order data for Pagar.me API
        order_data = {
            "amount": int(self.amount * 100),  # Convert to cents
            "currency": self.currency_id.name,
            "payments": [{
                "payment_method": "credit_card",
                "amount": int(self.amount * 100),
                "credit_card": {
                    "card_token": self.pagarme_token,
                }
            }],
            "customer": {
                "name": self.partner_name or "",
                "email": self.partner_email or "",
                "type": "individual",
            },
        }

        # Make API request to Pagar.me
        headers = {
            "Authorization": f"Bearer {self.acquirer_id.pagarme_api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            response = requests.post(
                "https://api.pagar.me/core/v5/orders",
                json=order_data,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            # Update transaction with response data
            self.acquirer_reference = result.get("id")
            
            # Set transaction status based on response
            status = result.get("status")
            if status == "paid":
                self._set_done()
            elif status == "pending":
                self._set_pending()
            else:
                self._set_error("Payment failed")
                
        except requests.RequestException as e:
            _logger.error("Pagar.me payment request failed: %s", e)
            self._set_error(f"Payment failed: {str(e)}")

    def _process_notification_data(self, notification_data):
        """Process notification data from Pagar.me webhooks."""
        if self.provider != "pagarme":
            return super()._process_notification_data(notification_data)

        status = notification_data.get("status")
        if status == "paid":
            self._set_done()
        elif status == "failed":
            self._set_error("Payment failed")
        elif status == "canceled":
            self._set_canceled()
        elif status == "pending":
            self._set_pending()