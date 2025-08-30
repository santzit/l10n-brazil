# Copyright 2024 OCA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("pagarme", "Pagar.me")], ondelete={"pagarme": "set default"}
    )
    pagarme_app_id = fields.Char(
        string="Public Key / App ID",
        help="Pagar.me Public Key (used for tokenization on frontend)",
        groups="base.group_system",
    )
    pagarme_api_key = fields.Char(
        string="Secret Key / API Key",
        help="Pagar.me Secret Key for server-side operations",
        groups="base.group_system",
    )

    def _compute_feature_support_fields(self):
        """Override of payment to enable transparent checkout features."""
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == "pagarme").update(
            {
                "support_tokenization": False,
                "support_express_checkout": False,
                "support_refund": "partial",
                # Explicitly disable redirect flow since we want inline
                "support_redirect_flow": False,
            }
        )

    def _compute_view_configuration_fields(self):
        """Override payment configuration to hide certain form elements."""
        super()._compute_view_configuration_fields()
        self.filtered(lambda p: p.code == "pagarme").update(
            {
                # Hide redirect-related configuration since we're inline-only
                "show_credentials_page": True,
                "show_allow_tokenization": True,
                "show_allow_express_checkout": False,
                "show_payment_icon_ids": True,
                "show_pre_msg": True,
                "show_pending_msg": True,
                "show_auth_msg": True,
                "show_done_msg": True,
                "show_cancel_msg": True,
            }
        )

    def _should_build_inline_form(self, is_validation=False):
        """Return whether the inline payment form should be instantiated.

        For Pagar.me, we always want to build the inline form for transparent checkout.

        :param bool is_validation: Whether the operation is a validation.
        :return: Whether the inline form should be instantiated.
        :rtype: bool
        """
        if self.code != "pagarme":
            return super()._should_build_inline_form(is_validation)
        
        # Always use inline form for Pagar.me (transparent checkout)
        return True

    def _get_redirect_form_view(self, is_validation=False):
        """Return the view of the template used to render the redirect form.
        
        For Pagar.me, we should never use redirect, so return None/False.

        :param bool is_validation: Whether the operation is a validation.
        :return: The view of the redirect form template.
        :rtype: record of `ir.ui.view`
        """
        if self.code != "pagarme":
            return super()._get_redirect_form_view(is_validation)
        
        # Pagar.me uses inline forms only, no redirect
        return False

    def _get_pagarme_webhook_url(self):
        """Get the webhook URL for Pagar.me notifications."""
        self.ensure_one()
        base_url = self.get_base_url()
        return f"{base_url}/payment/pagarme/webhook"



    def _get_specific_processing_values(self, processing_values):
        """Return specific processing values for Pagar.me provider."""
        res = super()._get_specific_processing_values(processing_values)
        if self.code != "pagarme":
            return res

        _logger.info("Pagar.me: Providing processing values for provider %s", self.name)

        pagarme_values = {
            "api_url": self._get_pagarme_api_url(),
            "webhook_url": self._get_pagarme_webhook_url(),
            "public_key": self.pagarme_app_id,  # Public key for frontend tokenization
            "app_id": self.pagarme_app_id,  # Legacy compatibility
            # Explicitly indicate this is a direct/inline payment
            "is_direct_payment": True,
            "flow": "direct",
        }
        
        res.update(pagarme_values)
        return res

    def _get_pagarme_api_url(self):
        """Get the Pagar.me API URL based on the provider state."""
        self.ensure_one()
        if self.state == "test":
            return "https://api.pagar.me/core/v5"
        return "https://api.pagar.me/core/v5"

    def action_test_connection(self):
        """Test connectivity to Pagar.me API."""
        self.ensure_one()

        if not self.pagarme_api_key:
            raise ValueError("API Key is required for connection testing")

        try:
            import requests
            from requests.auth import HTTPBasicAuth

            # Pagar.me uses Basic Authentication with secret key as username
            # and empty password
            auth = HTTPBasicAuth(self.pagarme_api_key, "")

            headers = {
                "Content-Type": "application/json",
            }

            _logger.info("Pagar.me: Testing connection for provider %s", self.name)
            api_url = self._get_pagarme_api_url()
            _logger.info("Pagar.me: Using API URL: %s/customers", api_url)

            # Test with a simple API call to check connection
            response = requests.get(
                f"{self._get_pagarme_api_url()}/customers",
                auth=auth,
                headers=headers,
                timeout=10,
                params={"page": 1, "size": 1},  # Minimal request
            )

            _logger.info(
                "Pagar.me: Connection test response - Status: %s", response.status_code
            )

            if response.status_code == 200:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Connection Successful",
                        "message": (
                            f"Successfully connected to Pagar.me API "
                            f"(Status: {response.status_code})"
                        ),
                        "type": "success",
                    },
                }
            else:
                error_msg = f"API returned status {response.status_code}"
                _logger.error("Pagar.me: Connection test failed - %s", error_msg)
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Connection Failed",
                        "message": error_msg,
                        "type": "danger",
                    },
                }

        except Exception as e:
            error_msg = f"Connection test failed: {str(e)}"
            _logger.error("Pagar.me: %s", error_msg)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Connection Failed",
                    "message": error_msg,
                    "type": "danger",
                },
            }
