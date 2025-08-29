# Copyright 2024 OCA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    pagarme_order_id = fields.Char(
        string="Pagar.me Order ID",
        help="Order ID from Pagar.me checkout session",
        readonly=True,
    )

    def _get_specific_processing_values(self, processing_values):
        """Return Pagar.me-specific processing values for redirect flow."""
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != "pagarme":
            return res

        # Create checkout session and get redirect URL
        checkout_url = self.provider_id._create_pagarme_checkout_session(self)
        
        return {
            "checkout_url": checkout_url,
        }

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Find transaction from Pagar.me notification data."""
        if provider_code != "pagarme":
            return super()._get_tx_from_notification_data(
                provider_code, notification_data
            )

        # Try to find by provider_reference (Pagar.me order ID)
        provider_reference = notification_data.get("id")
        if provider_reference:
            tx = self.search([("provider_reference", "=", provider_reference)], limit=1)
            if tx:
                return tx

        # Try to find by reference in metadata
        metadata = notification_data.get("metadata", {})
        odoo_reference = metadata.get("odoo_reference")
        if odoo_reference:
            tx = self.search([("reference", "=", odoo_reference)], limit=1)
            if tx:
                return tx

        raise ValueError(
            f"No transaction found for Pagar.me notification: {notification_data}"
        )

    def _process_notification_data(self, notification_data):
        """Process notification data from Pagar.me webhooks."""
        if self.provider_code != "pagarme":
            return super()._process_notification_data(notification_data)

        # Update provider reference if not set
        if not self.provider_reference and notification_data.get("id"):
            self.provider_reference = notification_data.get("id")

        # Process payment status
        status = notification_data.get("status")
        if status == "paid":
            self._set_done()
        elif status == "failed":
            self._set_error("Payment failed")
        elif status == "canceled":
            self._set_canceled()
        elif status == "pending":
            self._set_pending()
        else:
            _logger.warning("Unknown Pagar.me status: %s", status)
