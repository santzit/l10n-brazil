# Copyright 2024 OCA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


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

    def _get_default_payment_method_codes(self):
        """Return the default payment method codes."""
        default_codes = super()._get_default_payment_method_codes()
        if self.code == "pagarme":
            default_codes.append("card")
        return default_codes

    def _get_specific_processing_values(self, processing_values):
        """Return specific processing values for Pagar.me provider."""
        res = super()._get_specific_processing_values(processing_values)
        if self.code != "pagarme":
            return res

        return {
            "api_url": self._get_pagarme_api_url(),
            "webhook_url": self._get_pagarme_webhook_url(),
            "app_id": self.pagarme_app_id,
        }

    def _get_pagarme_api_url(self):
        """Get the Pagar.me API URL based on the provider state."""
        self.ensure_one()
        if self.state == "test":
            return "https://api.pagar.me/1/test"
        return "https://api.pagar.me/1"

    def _send_payment_request(self, payload):
        """Send payment request to Pagar.me API."""
        # This would implement the actual API call to Pagar.me
        # For now, return a placeholder response
        return {"status": "success", "transaction_id": "pagarme_test_txn"}
