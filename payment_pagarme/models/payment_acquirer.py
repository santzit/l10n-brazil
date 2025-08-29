# Copyright 2024 OCA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import requests

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

PAGARME_API_URL = "https://api.pagar.me/core/v5"


class PaymentAcquirer(models.Model):
    _inherit = "payment.acquirer"

    provider = fields.Selection(
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
    pagarme_webhook_url = fields.Char(
        string="Webhook URL",
        help="URL for Pagar.me webhooks",
        readonly=True,
        compute="_compute_pagarme_webhook_url",
    )

    def _compute_pagarme_webhook_url(self):
        """Compute the webhook URL for Pagar.me notifications."""
        for acquirer in self:
            if acquirer.provider == "pagarme":
                base_url = acquirer.get_base_url()
                acquirer.pagarme_webhook_url = f"{base_url}/payment/pagarme/webhook"
            else:
                acquirer.pagarme_webhook_url = False

    @api.constrains("pagarme_app_id", "pagarme_api_key")
    def _check_pagarme_credentials(self):
        """Validate Pagar.me credentials."""
        for acquirer in self:
            if acquirer.provider == "pagarme":
                if not acquirer.pagarme_app_id:
                    raise ValidationError(_("Pagar.me App ID is required."))
                if not acquirer.pagarme_api_key:
                    raise ValidationError(_("Pagar.me API Key is required."))

    def _pagarme_get_api_headers(self):
        """Get headers for Pagar.me API requests."""
        self.ensure_one()
        return {
            "Authorization": f"Bearer {self.pagarme_api_key}",
            "Content-Type": "application/json",
        }

    def _pagarme_make_request(self, endpoint, data=None, method="POST"):
        """Make a request to Pagar.me API."""
        self.ensure_one()
        url = f"{PAGARME_API_URL}{endpoint}"
        headers = self._pagarme_get_api_headers()
        
        try:
            if method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            _logger.error("Pagar.me API request failed: %s", e)
            raise ValidationError(_("Communication with Pagar.me failed: %s") % str(e))

    def pagarme_form_generate_values(self, values):
        """Generate form values for Pagar.me payment form."""
        self.ensure_one()
        
        base_url = self.get_base_url()
        pagarme_values = {
            "app_id": self.pagarme_app_id,
            "return_url": f"{base_url}/payment/pagarme/return",
            "reference": values.get("reference"),
            "amount": int((values.get("amount", 0) * 100)),  # Convert to cents
            "currency": values.get("currency", "BRL"),
            "partner_name": values.get("partner_name", ""),
            "partner_email": values.get("partner_email", ""),
            "partner_phone": values.get("partner_phone", ""),
        }
        
        values.update(pagarme_values)
        return values

    def _get_default_payment_method_codes(self):
        """Return the default payment method codes."""
        default_codes = super()._get_default_payment_method_codes()
        if self.provider == "pagarme":
            default_codes.append("card")
        return default_codes