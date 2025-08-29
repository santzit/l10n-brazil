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
