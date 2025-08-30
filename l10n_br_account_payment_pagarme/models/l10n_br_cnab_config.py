# Copyright 2024 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..constants.pagarme_api import (
    PAGARME_ANTIFRAUD_RULES,
    PAGARME_PAYMENT_METHODS,
    PAGARME_PIX_KEY_TYPES,
)

_logger = logging.getLogger(__name__)


class L10nBrCnabConfig(models.Model):
    """CNAB Configuration extension for Pagar.me."""
    
    _inherit = "l10n_br_cnab_config"

    # Pagar.me processor selection
    cnab_processor = fields.Selection(
        selection_add=[("pagarme", "Pagar.me")],
        ondelete={"pagarme": "set default"}
    )

    # Pagar.me API Configuration
    pagarme_api_key = fields.Char(
        string="Pagar.me API Key",
        help="Your Pagar.me API Secret Key",
        groups="base.group_system"
    )

    pagarme_public_key = fields.Char(
        string="Pagar.me Public Key",
        help="Your Pagar.me Public Key for client-side encryption"
    )

    pagarme_webhook_secret = fields.Char(
        string="Webhook Secret",
        help="Secret key for webhook signature validation",
        groups="base.group_system"
    )

    pagarme_recipient_id = fields.Char(
        string="Recipient ID",
        help="Pagar.me recipient identifier for receiving payments"
    )

    pagarme_sandbox_mode = fields.Boolean(
        string="Sandbox Mode",
        default=True,
        help="Enable to use Pagar.me sandbox environment"
    )

    # Payment Method Configuration
    pagarme_payment_method = fields.Selection(
        selection=PAGARME_PAYMENT_METHODS,
        string="Payment Method",
        help="Payment method to use for this configuration"
    )

    pagarme_enable_multiple_methods = fields.Boolean(
        string="Enable Multiple Payment Methods",
        default=False,
        help="Allow customers to choose payment method"
    )

    # Credit Card Configuration
    pagarme_max_installments = fields.Integer(
        string="Max Installments",
        default=12,
        help="Maximum number of installments for credit card payments"
    )

    pagarme_min_installment_amount = fields.Float(
        string="Min Installment Amount (R$)",
        default=5.00,
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

    pagarme_interest_rate = fields.Float(
        string="Interest Rate (%)",
        default=0.0,
        help="Interest rate for installment payments"
    )

    # Boleto Configuration
    pagarme_boleto_expiration_days = fields.Integer(
        string="Boleto Expiration Days",
        default=3,
        help="Number of days until boleto expires"
    )

    pagarme_boleto_instructions = fields.Text(
        string="Boleto Instructions",
        default="Pay only with this boleto",
        help="Payment instructions to be printed on boleto"
    )

    pagarme_boleto_bank = fields.Selection([
        ("237", "Bradesco"),
        ("341", "Itaú"),
        ("033", "Santander"),
        ("001", "Banco do Brasil"),
        ("104", "Caixa Econômica Federal"),
    ],
        string="Boleto Bank",
        help="Bank to use for boleto generation"
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

    pagarme_antifraud_threshold = fields.Float(
        string="Fraud Score Threshold",
        default=50.0,
        help="Minimum fraud score to reject transaction (0-100)"
    )

    # Split Payment Configuration
    pagarme_enable_split = fields.Boolean(
        string="Enable Split Payments",
        default=False,
        help="Enable automatic payment splitting"
    )

    pagarme_split_rules = fields.Text(
        string="Split Rules (JSON)",
        help="JSON configuration for payment split rules"
    )

    # Webhook Configuration
    pagarme_webhook_url = fields.Char(
        string="Webhook URL",
        compute="_compute_pagarme_webhook_url",
        help="URL for receiving Pagar.me webhooks"
    )

    # Subscription Configuration (for future use)
    pagarme_enable_subscriptions = fields.Boolean(
        string="Enable Subscriptions",
        default=False,
        help="Enable subscription/recurring payments"
    )

    @api.depends("cnab_processor")
    def _compute_pagarme_webhook_url(self):
        """Compute the webhook URL for Pagar.me."""
        for config in self:
            if config.cnab_processor == "pagarme":
                base_url = config.get_base_url()
                config.pagarme_webhook_url = f"{base_url}/payment/pagarme/webhook/{config.id}"
            else:
                config.pagarme_webhook_url = False

    @api.constrains("pagarme_max_installments")
    def _check_pagarme_max_installments(self):
        """Validate maximum installments."""
        for config in self:
            if config.cnab_processor == "pagarme" and config.pagarme_max_installments:
                if config.pagarme_max_installments < 1 or config.pagarme_max_installments > 24:
                    raise ValidationError(_("Maximum installments must be between 1 and 24"))

    @api.constrains("pagarme_min_installment_amount")
    def _check_pagarme_min_installment_amount(self):
        """Validate minimum installment amount."""
        for config in self:
            if config.cnab_processor == "pagarme" and config.pagarme_min_installment_amount:
                if config.pagarme_min_installment_amount < 1.00:
                    raise ValidationError(_("Minimum installment amount must be at least R$ 1.00"))

    @api.constrains("pagarme_antifraud_threshold")
    def _check_pagarme_antifraud_threshold(self):
        """Validate anti-fraud threshold."""
        for config in self:
            if config.cnab_processor == "pagarme" and config.pagarme_antifraud_threshold:
                if config.pagarme_antifraud_threshold < 0 or config.pagarme_antifraud_threshold > 100:
                    raise ValidationError(_("Anti-fraud threshold must be between 0 and 100"))

    @api.constrains("pagarme_split_rules")
    def _check_pagarme_split_rules(self):
        """Validate split rules JSON format."""
        for config in self:
            if config.cnab_processor == "pagarme" and config.pagarme_split_rules:
                try:
                    import json
                    json.loads(config.pagarme_split_rules)
                except json.JSONDecodeError:
                    raise ValidationError(_("Split rules must be valid JSON format"))

    def _check_cnab_restriction(self):
        """Override to add Pagar.me specific validations."""
        super()._check_cnab_restriction()
        
        if self.cnab_processor == "pagarme":
            self._check_pagarme_configuration()

    def _check_pagarme_configuration(self):
        """Check Pagar.me specific configuration."""
        if not self.pagarme_api_key:
            raise ValidationError(_("Pagar.me API key is required"))
            
        if not self.pagarme_public_key:
            raise ValidationError(_("Pagar.me public key is required"))
            
        if not self.pagarme_payment_method and not self.pagarme_enable_multiple_methods:
            raise ValidationError(_("Payment method must be specified or multiple methods enabled"))
            
        # Validate PIX configuration
        if self.pagarme_payment_method == "pix" or self.pagarme_enable_multiple_methods:
            if self.pagarme_pix_key_type != "random" and not self.pagarme_pix_key:
                raise ValidationError(_("PIX key is required when not using random key type"))

    def _pagarme_make_request(self, endpoint, data=None, method="POST"):
        """Make request to Pagar.me API (delegate to payment provider)."""
        # Find corresponding payment provider
        provider = self.env["payment.provider"].search([
            ("code", "=", "pagarme"),
            ("pagarme_api_key", "=", self.pagarme_api_key)
        ], limit=1)
        
        if not provider:
            # Create temporary provider for API calls
            provider = self.env["payment.provider"].create({
                "name": f"Pagar.me - {self.name}",
                "code": "pagarme",
                "pagarme_api_key": self.pagarme_api_key,
                "pagarme_public_key": self.pagarme_public_key,
                "pagarme_sandbox_mode": self.pagarme_sandbox_mode,
                "state": "test" if self.pagarme_sandbox_mode else "enabled",
            })
            
        return provider._pagarme_make_request(endpoint, data, method)

    def action_test_pagarme_connection(self):
        """Test connection to Pagar.me API."""
        self.ensure_one()
        
        if self.cnab_processor != "pagarme":
            return
            
        try:
            response = self._pagarme_make_request("balance", method="GET")
            message = _("Connection successful! Available balance: R$ %s") % (
                response.get("available", {}).get("amount", 0) / 100
            )
            message_type = "success"
            title = _("Pagar.me Connection Test")
        except Exception as e:
            message = _("Connection failed: %s") % str(e)
            message_type = "danger" 
            title = _("Pagar.me Connection Test")
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': message_type,
                'sticky': True,
            }
        }

    def action_pagarme_webhook_setup(self):
        """Setup webhooks in Pagar.me."""
        self.ensure_one()
        
        if self.cnab_processor != "pagarme":
            return
            
        webhook_data = {
            "url": self.pagarme_webhook_url,
            "events": [
                "transaction.paid",
                "transaction.refused",
                "transaction.refunded",
                "charge.paid",
                "charge.failed",
                "order.paid",
                "order.canceled",
            ],
            "description": f"Odoo Webhook - {self.name}"
        }
        
        try:
            response = self._pagarme_make_request("hooks", webhook_data)
            webhook_id = response.get("id")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Webhook Setup"),
                    'message': _("Webhook created successfully! ID: %s") % webhook_id,
                    'type': 'success',
                    'sticky': True,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Webhook Setup"),
                    'message': _("Error creating webhook: %s") % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }