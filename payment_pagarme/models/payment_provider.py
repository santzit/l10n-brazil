# Copyright 2024 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import requests
from urllib.parse import urljoin

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("pagarme", "Pagar.me")],
        ondelete={"pagarme": "set default"}
    )

    # Pagar.me specific configuration fields
    pagarme_api_key = fields.Char(
        string="Pagar.me API Key",
        help="Your Pagar.me API key (starts with sk_)",
        required_if_provider="pagarme",
        groups="base.group_system",
    )
    pagarme_encryption_key = fields.Char(
        string="Pagar.me Encryption Key",
        help="Pagar.me encryption key for card data encryption",
        required_if_provider="pagarme",
        groups="base.group_system",
    )
    pagarme_webhook_url = fields.Char(
        string="Webhook URL",
        help="This URL will be automatically configured. Use it in your Pagar.me dashboard.",
        compute="_compute_pagarme_webhook_url",
        readonly=True,
    )
    pagarme_max_installments = fields.Integer(
        string="Maximum Installments",
        default=12,
        help="Maximum number of installments allowed",
    )
    pagarme_min_installment_amount = fields.Float(
        string="Minimum Installment Amount",
        default=5.0,
        help="Minimum amount per installment in BRL",
    )

    #=== COMPUTE METHODS ===#

    @api.depends('code')
    def _compute_feature_support_fields(self):
        """Override to enable additional features for Pagar.me."""
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'pagarme').update({
            'support_manual_capture': False,
            'support_refund': 'partial',
            'support_tokenization': False,
            'support_express_checkout': False,
        })

    @api.depends("code")
    def _compute_pagarme_webhook_url(self):
        """Compute the webhook URL for Pagar.me."""
        for provider in self:
            if provider.code == "pagarme":
                base_url = provider.get_base_url()
                provider.pagarme_webhook_url = urljoin(base_url, "/payment/pagarme/webhook")
            else:
                provider.pagarme_webhook_url = False

    #=== CONSTRAINT METHODS ===#

    @api.constrains("pagarme_api_key")
    def _check_pagarme_api_key(self):
        """Validate Pagar.me API key format."""
        for provider in self:
            if provider.code == "pagarme" and provider.pagarme_api_key:
                if not provider.pagarme_api_key.startswith("sk_"):
                    raise ValidationError(_("Pagar.me API key must start with 'sk_'"))

    #=== BUSINESS METHODS ===#

    def _get_specific_processing_values(self, processing_values):
        """Return Pagar.me-specific processing values for inline form."""
        res = super()._get_specific_processing_values(processing_values)
        if self.code != "pagarme":
            return res

        _logger.info("=== PAGAR.ME PROVIDER PROCESSING VALUES DEBUG ===")
        _logger.info("Provider: %s (ID: %s)", self.name, self.id)
        _logger.info("Input processing_values: %s", processing_values)
        
        # Extract transaction from processing_values
        tx_sudo = processing_values.get('tx_sudo')
        if not tx_sudo:
            _logger.error("Pagar.me: No transaction found in processing_values")
            return res
            
        _logger.info("Transaction found: %s (ID: %s, reference: %s)", tx_sudo.reference, tx_sudo.id, tx_sudo.reference)
        
        # Ensure access token exists
        if not tx_sudo.access_token:
            tx_sudo.access_token = tx_sudo._portal_ensure_token()
            
        # Provide essential transaction context to template
        pagarme_values = {
            'reference': tx_sudo.reference,
            'provider_id': self.id,
            'access_token': tx_sudo.access_token,
            'amount': tx_sudo.amount,
            'currency': tx_sudo.currency_id.name,
            'tx': tx_sudo,  # Provide transaction object to template
            'api_key': self.pagarme_api_key,
            'encryption_key': self.pagarme_encryption_key,
        }
        
        _logger.info("Pagarme processing values being returned: %s", {k: ('***' if 'key' in k.lower() else v) for k, v in pagarme_values.items()})
        _logger.info("=== END PAGAR.ME PROVIDER PROCESSING VALUES DEBUG ===")
        
        res.update(pagarme_values)
        return res

    def _pagarme_make_request(self, endpoint, data=None, method="POST"):
        """Make a request to Pagar.me API."""
        if self.code != "pagarme":
            return super()._pagarme_make_request(endpoint, data, method)

        if not self.pagarme_api_key:
            raise UserError(_("Pagar.me API key is not configured"))

        # Determine base URL based on environment
        base_url = "https://api.pagar.me/core/v5/"

        url = urljoin(base_url, endpoint)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.pagarme_api_key}:",
        }

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, headers=headers, timeout=30)
            else:
                raise UserError(_("Unsupported HTTP method: %s") % method)

            response.raise_for_status()
            
            if response.content:
                return response.json()
            else:
                return {}

        except requests.exceptions.Timeout:
            raise UserError(_("Timeout while communicating with Pagar.me"))
        except requests.exceptions.ConnectionError:
            raise UserError(_("Connection error while communicating with Pagar.me"))
        except requests.exceptions.HTTPError as e:
            error_msg = _("HTTP error while communicating with Pagar.me: %s") % e
            
            # Try to extract error details from response
            try:
                error_data = e.response.json() if e.response.content else {}
                if "errors" in error_data:
                    error_details = []
                    for error in error_data["errors"]:
                        error_details.append(f"{error.get('field', 'general')}: {error.get('message', str(error))}")
                    error_msg += "\nDetails: " + "; ".join(error_details)
            except (ValueError, AttributeError):
                pass
                
            raise UserError(error_msg)
        except Exception as e:
            raise UserError(_("Unexpected error while communicating with Pagar.me: %s") % str(e))



