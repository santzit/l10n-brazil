# Copyright 2024 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import json
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..constants.pagarme_api import (
    PAGARME_ANTIFRAUD_RULES,
    PAGARME_API_TIMEOUT,
    PAGARME_DOCUMENT_TYPES,
    PAGARME_MAX_INSTALLMENTS,
    PAGARME_MIN_INSTALLMENT_AMOUNT,
    PAGARME_PAYMENT_METHODS,
    PAGARME_PIX_KEY_TYPES,
    PAGARME_SUPPORTED_CARD_BRANDS,
    PAGARME_WEBHOOK_EVENTS,
    get_pagarme_api_url,
    get_pagarme_headers,
)

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    """Payment Provider for Pagar.me integration."""
    
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("pagarme", "Pagar.me")],
        ondelete={"pagarme": "set default"}
    )

    # Pagar.me Configuration Fields
    pagarme_api_key = fields.Char(
        string="API Key",
        required_if_provider="pagarme",
        groups="base.group_system",
        help="Your Pagar.me API Secret Key"
    )

    pagarme_public_key = fields.Char(
        string="Public Key", 
        required_if_provider="pagarme",
        help="Your Pagar.me Public Key for client-side encryption"
    )

    pagarme_webhook_secret = fields.Char(
        string="Webhook Secret",
        groups="base.group_system",
        help="Secret key for webhook signature validation"
    )

    pagarme_sandbox_mode = fields.Boolean(
        string="Sandbox Mode",
        default=True,
        help="Enable to use Pagar.me sandbox environment"
    )

    # Payment Method Configuration
    pagarme_enable_credit_card = fields.Boolean(
        string="Enable Credit Card",
        default=True,
        help="Allow credit card payments"
    )

    pagarme_enable_debit_card = fields.Boolean(
        string="Enable Debit Card", 
        default=True,
        help="Allow debit card payments"
    )

    pagarme_enable_boleto = fields.Boolean(
        string="Enable Boleto",
        default=True,
        help="Allow boleto bancário payments"
    )

    pagarme_enable_pix = fields.Boolean(
        string="Enable PIX",
        default=True,
        help="Allow PIX payments"
    )

    # Credit Card Configuration
    pagarme_max_installments = fields.Integer(
        string="Max Installments",
        default=PAGARME_MAX_INSTALLMENTS,
        help="Maximum number of installments for credit card payments"
    )

    pagarme_min_installment_amount = fields.Float(
        string="Min Installment Amount (R$)",
        default=PAGARME_MIN_INSTALLMENT_AMOUNT,
        help="Minimum amount per installment"
    )

    pagarme_capture_method = fields.Selection([
        ("automatic", "Automatic Capture"),
        ("manual", "Manual Capture"),
    ], 
        string="Capture Method",
        default="automatic",
        help="How to capture authorized transactions"
    )

    # Boleto Configuration  
    pagarme_boleto_expiration_days = fields.Integer(
        string="Boleto Expiration Days",
        default=3,
        help="Number of days until boleto expires"
    )

    pagarme_boleto_instructions = fields.Text(
        string="Boleto Instructions",
        help="Payment instructions to be printed on boleto"
    )

    # PIX Configuration
    pagarme_pix_expiration_minutes = fields.Integer(
        string="PIX Expiration Minutes", 
        default=60,
        help="Number of minutes until PIX payment expires"
    )

    pagarme_pix_key_type = fields.Selection(
        selection=PAGARME_PIX_KEY_TYPES,
        string="PIX Key Type",
        default="random",
        help="Type of PIX key to use for payments"
    )

    pagarme_pix_key = fields.Char(
        string="PIX Key",
        help="Your PIX key for receiving payments"
    )

    # Anti-fraud Configuration
    pagarme_antifraud_enabled = fields.Boolean(
        string="Enable Anti-fraud",
        default=False,
        help="Enable Pagar.me anti-fraud analysis"
    )

    pagarme_antifraud_rule = fields.Selection(
        selection=PAGARME_ANTIFRAUD_RULES,
        string="Anti-fraud Rule",
        default="automatic",
        help="Anti-fraud analysis configuration"
    )

    # Webhook Configuration
    pagarme_webhook_url = fields.Char(
        string="Webhook URL",
        compute="_compute_webhook_url",
        help="URL for receiving Pagar.me webhooks"
    )

    pagarme_webhook_events = fields.Selection(
        selection=[(event, event.replace("_", " ").title()) for event in PAGARME_WEBHOOK_EVENTS],
        string="Webhook Events",
        help="Events to receive via webhook"
    )

    @api.depends("code")
    def _compute_webhook_url(self):
        """Compute the webhook URL for this provider."""
        for provider in self:
            if provider.code == "pagarme":
                base_url = provider.get_base_url()
                provider.pagarme_webhook_url = f"{base_url}/payment/pagarme/webhook"
            else:
                provider.pagarme_webhook_url = False

    @api.constrains("pagarme_max_installments")
    def _check_max_installments(self):
        """Validate maximum installments."""
        for provider in self:
            if provider.code == "pagarme" and provider.pagarme_max_installments:
                if provider.pagarme_max_installments < 1 or provider.pagarme_max_installments > 24:
                    raise ValidationError(_("Maximum installments must be between 1 and 24"))

    @api.constrains("pagarme_min_installment_amount")
    def _check_min_installment_amount(self):
        """Validate minimum installment amount.""" 
        for provider in self:
            if provider.code == "pagarme" and provider.pagarme_min_installment_amount:
                if provider.pagarme_min_installment_amount < 1.00:
                    raise ValidationError(_("Minimum installment amount must be at least R$ 1.00"))

    def _get_supported_currencies(self):
        """Override to return BRL for Pagar.me."""
        supported_currencies = super()._get_supported_currencies()
        if self.code == "pagarme":
            supported_currencies = supported_currencies.filtered(lambda c: c.name == "BRL")
        return supported_currencies

    def _pagarme_make_request(self, endpoint, data=None, method="POST"):
        """
        Make a request to the Pagar.me API.
        
        Args:
            endpoint: API endpoint 
            data: Request data
            method: HTTP method
            
        Returns:
            dict: API response
        """
        if not self.pagarme_api_key:
            raise UserError(_("Pagar.me API key is not configured"))

        url = get_pagarme_api_url(self.env, endpoint)
        headers = get_pagarme_headers(self._pagarme_get_encoded_api_key())

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=PAGARME_API_TIMEOUT)
            elif method == "POST":
                response = requests.post(
                    url, headers=headers, json=data, timeout=PAGARME_API_TIMEOUT
                )
            elif method == "PUT":
                response = requests.put(
                    url, headers=headers, json=data, timeout=PAGARME_API_TIMEOUT
                )
            else:
                raise UserError(_("Unsupported HTTP method: %s") % method)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            raise UserError(_("Timeout connecting to Pagar.me API"))
        except requests.exceptions.ConnectionError:
            raise UserError(_("Error connecting to Pagar.me API"))
        except requests.exceptions.HTTPError as e:
            error_msg = _("Pagar.me API error: %s") % str(e)
            if hasattr(e.response, 'json'):
                try:
                    error_data = e.response.json()
                    if 'message' in error_data:
                        error_msg = error_data['message']
                except:
                    pass
            raise UserError(error_msg)

    def _pagarme_get_encoded_api_key(self):
        """Get base64 encoded API key for authentication."""
        api_key_with_colon = f"{self.pagarme_api_key}:"
        encoded_key = base64.b64encode(api_key_with_colon.encode()).decode()
        return encoded_key

    def _pagarme_test_connection(self):
        """Test connection to Pagar.me API."""
        try:
            # Test by getting account balance or making a simple API call
            response = self._pagarme_make_request("balance", method="GET")
            return True, _("Connection successful")
        except Exception as e:
            return False, str(e)

    def action_test_pagarme_connection(self):
        """Action to test Pagar.me API connection."""
        self.ensure_one()
        if self.code != "pagarme":
            return
            
        success, message = self._pagarme_test_connection()
        
        if success:
            title = _("Connection Successful")
            message_type = 'success'
        else:
            title = _("Connection Failed")
            message_type = 'danger'
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': message_type,
                'sticky': False,
            }
        }