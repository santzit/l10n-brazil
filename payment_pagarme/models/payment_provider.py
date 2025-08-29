# Copyright 2024 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
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
            'support_express_checkout': True,  # Enable redirect checkout
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

    @api.constrains("state", "pagarme_api_key")
    def _check_pagarme_configuration(self):
        """Validate that required Pagar.me configuration is present when enabled.""" 
        for provider in self:
            if provider.code == "pagarme" and provider.state in ('enabled', 'test'):
                if not provider.pagarme_api_key:
                    raise ValidationError(_(
                        "Pagar.me API key is required when the provider is enabled. "
                        "Please configure your Pagar.me credentials before enabling the provider."
                    ))

    @api.constrains("pagarme_api_key")
    def _check_pagarme_api_key(self):
        """Validate Pagar.me API key format."""
        for provider in self:
            if provider.code == "pagarme" and provider.pagarme_api_key:
                if not provider.pagarme_api_key.startswith("sk_"):
                    raise ValidationError(_("Pagar.me API key must start with 'sk_'"))

    #=== BUSINESS METHODS ===#

    def _get_redirect_form_view(self, is_validation=False):
        """Return the form view for redirect payment flow."""
        if self.code != 'pagarme':
            return super()._get_redirect_form_view(is_validation)
        return self.env.ref('payment_pagarme.redirect_form')

    def _pagarme_make_request(self, endpoint, data=None, method="POST"):
        """Make a request to Pagar.me API."""
        if self.code != "pagarme":
            raise UserError(_("This method is only available for Pagar.me providers"))

        if not self.pagarme_api_key:
            raise UserError(_("Pagar.me API key is not configured"))

        # Determine base URL based on environment
        base_url = "https://api.pagar.me/core/v5/"

        url = urljoin(base_url, endpoint)
        
        # Encode API key for Basic Auth (API key as username, empty password)
        auth_string = f"{self.pagarme_api_key}:"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_auth}",
        }

        _logger.info("Pagar.me API: Making %s request to %s", method, url)
        _logger.debug("Pagar.me API: Headers: %s", {k: '***' if k == 'Authorization' else v for k, v in headers.items()})
        if data:
            _logger.debug("Pagar.me API: Request data: %s", data)

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, headers=headers, timeout=30)
            else:
                raise UserError(_("Unsupported HTTP method: %s") % method)

            _logger.info("Pagar.me API: Response status: %s", response.status_code)
            _logger.debug("Pagar.me API: Response headers: %s", dict(response.headers))
            
            response.raise_for_status()
            
            if response.content:
                response_data = response.json()
                _logger.debug("Pagar.me API: Response data: %s", response_data)
                return response_data
            else:
                return {}

        except requests.exceptions.Timeout:
            _logger.error("Pagar.me API: Timeout after 30 seconds for URL: %s", url)
            raise UserError(_("Timeout while communicating with Pagar.me"))
        except requests.exceptions.ConnectionError as e:
            _logger.error("Pagar.me API: Connection error for URL %s: %s", url, e)
            raise UserError(_("Connection error while communicating with Pagar.me"))
        except requests.exceptions.HTTPError as e:
            error_msg = _("HTTP error while communicating with Pagar.me: %s") % e
            _logger.error("Pagar.me API: HTTP error %s for URL %s", e, url)
            
            # Try to extract error details from response
            try:
                error_data = e.response.json() if e.response.content else {}
                _logger.error("Pagar.me API: Error response data: %s", error_data)
                if "errors" in error_data:
                    error_details = []
                    for error in error_data["errors"]:
                        error_details.append(f"{error.get('field', 'general')}: {error.get('message', str(error))}")
                    error_msg += "\nDetails: " + "; ".join(error_details)
            except (ValueError, AttributeError):
                pass
                
            raise UserError(error_msg)
        except Exception as e:
            _logger.error("Pagar.me API: Unexpected error for URL %s: %s", url, e, exc_info=True)
            raise UserError(_("Unexpected error while communicating with Pagar.me: %s") % str(e))



