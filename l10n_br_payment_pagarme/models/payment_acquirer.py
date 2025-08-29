# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import pprint

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

# Import removed to avoid circular import - controller imported at runtime

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = "payment.acquirer"

    provider = fields.Selection(
        selection_add=[("pagarme", "Pagar.me")], ondelete={"pagarme": "set default"}
    )
    pagarme_api_key = fields.Char(
        string="API Key", 
        help="Pagar.me API Key",
        groups="base.group_user"
    )
    pagarme_encryption_key = fields.Char(
        string="Encryption Key",
        help="Pagar.me Encryption Key for frontend tokenization", 
        groups="base.group_user"
    )
    pagarme_webhook_secret = fields.Char(
        string="Webhook Secret",
        help="Secret for webhook signature validation",
        groups="base.group_user"
    )

    @api.model 
    def _get_compatible_acquirers(self, *args, currency_id=None, **kwargs):
        """ Override to filter Pagar.me acquirer based on currency. """
        acquirers = super()._get_compatible_acquirers(*args, currency_id=currency_id, **kwargs)
        currency = self.env["res.currency"].browse(currency_id)
        
        if currency and currency.name != "BRL":
            # Pagar.me only supports Brazilian Real (BRL)
            acquirers = acquirers.filtered(lambda acq: acq.provider != "pagarme")
            
        return acquirers

    def _pagarme_get_api_url(self):
        """ Return the appropriate Pagar.me API URL based on state. """
        self.ensure_one()
        if self.state == "enabled":
            return "https://api.pagar.me/core/v5"
        else:
            return "https://api.pagar.me/core/v5"  # Pagar.me uses same URL for test/prod

    def _pagarme_make_request(self, endpoint, data=None, method="POST"):
        """ Make a request to Pagar.me API. """
        self.ensure_one()
        import requests
        
        url = f"{self._pagarme_get_api_url()}{endpoint}"
        headers = {
            "Authorization": f"Basic {self.pagarme_api_key}",
            "Content-Type": "application/json",
        }
        
        _logger.info(
            "Sending request to Pagar.me API:\nURL: %s\nData: %s", 
            url, pprint.pformat(data) if data else "None"
        )
        
        try:
            if method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            else:
                raise UserError(_("Unsupported HTTP method: %s") % method)
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as error:
            _logger.exception("Error communicating with Pagar.me API")
            raise UserError(
                _("Could not establish the connection to Pagar.me API.\n%s") % str(error)
            )

    def _pagarme_create_charge(self, transaction_data):
        """ Create a charge on Pagar.me API. """
        self.ensure_one()
        
        charge_data = {
            "amount": int(transaction_data["amount"] * 100),  # Convert to cents
            "currency": "BRL",
            "payment_method": "credit_card",
            "code": transaction_data["reference"],
            "customer": {
                "name": transaction_data.get("partner_name", ""),
                "email": transaction_data.get("partner_email", ""),
                "document": transaction_data.get("partner_vat", ""),
                "document_type": "CPF" if len(transaction_data.get("partner_vat", "")) == 11 else "CNPJ",
            },
            "card_token": transaction_data["card_token"],
        }
        
        if transaction_data.get("billing_address"):
            charge_data["billing_address"] = transaction_data["billing_address"]
            
        return self._pagarme_make_request("/charges", charge_data)

    @api.model
    def _get_default_payment_method_id(self):
        return self.env.ref("l10n_br_payment_pagarme.payment_method_pagarme").id

    def _get_supported_currencies(self):
        """ Override to return supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.provider == "pagarme":
            supported_currencies = supported_currencies.filtered(lambda c: c.name == "BRL")
        return supported_currencies

    @api.constrains("state", "pagarme_api_key")
    def _check_required_if_provider_pagarme(self):
        """ Check that required fields are set if provider is Pagar.me. """
        for record in self:
            if (
                record.provider == "pagarme"
                and record.state != "disabled" 
                and not record.pagarme_api_key
            ):
                raise ValidationError(_("API Key is required for Pagar.me."))