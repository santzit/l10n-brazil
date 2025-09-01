# Copyright 2024 OCA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    pagarme_token = fields.Char(
        string="Pagar.me Token",
        help="Token received from Pagar.me tokenization",
        readonly=True,
    )
    capture_manually = fields.Boolean(related="provider_id.capture_manually")

    def _get_specific_processing_values(self, processing_values):
        """Return Pagar.me-specific processing values."""
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != "pagarme":
            return res

        # Return specific keys expected by the payment framework, similar to demo
        return {
            "public_key": self.provider_id.pagarme_app_id,
            "api_key": self.provider_id.pagarme_api_key,
            "amount": int(self.amount * 100),  # Convert to cents for Pagar.me API
            "currency": self.currency_id.name.lower(),
        }

    def _send_payment_request(self):
        """Send payment request to Pagar.me using Order API."""
        if self.provider_code != "pagarme":
            return super()._send_payment_request()

        # For Pagar.me, payment processing is handled by the controller
        # which calls the API directly. This method is kept for compatibility
        # but the actual processing happens in the controller.
        _logger.info(
            "Pagar.me: Payment request delegated to controller for transaction %s",
            self.reference,
        )

    def _process_notification_data(self, notification_data):
        """Process notification data from Pagar.me webhooks."""
        if self.provider_code != "pagarme":
            return super()._process_notification_data(notification_data)

        _logger.info(
            "Pagar.me: Processing webhook notification for transaction %s",
            self.reference,
        )
        _logger.info("Pagar.me: Webhook data: %s", json.dumps(notification_data))

        # Handle both webhook format and direct order data format
        event_type = notification_data.get("type")
        if event_type:
            # Webhook format with event type
            event_data = notification_data.get("data", {})

            if event_type == "order.paid":
                # Check if manual capture is enabled like payment_demo
                manual_capture = notification_data.get("manual_capture", False)
                if self.provider_id.capture_manually and not manual_capture:
                    self._set_authorized()
                    _logger.info(
                        "Pagar.me: Transaction %s marked as authorized via webhook",
                        self.reference,
                    )
                else:
                    self._set_done()
                    _logger.info(
                        "Pagar.me: Transaction %s marked as done via webhook",
                        self.reference,
                    )
            elif event_type == "order.payment_failed":
                error_message = event_data.get("reason", "Payment failed")
                self._set_error(error_message)
                _logger.error(
                    "Pagar.me: Transaction %s failed via webhook: %s",
                    self.reference,
                    error_message,
                )
            elif event_type == "order.canceled":
                self._set_canceled()
                _logger.info(
                    "Pagar.me: Transaction %s marked as canceled via webhook",
                    self.reference,
                )
            elif event_type in ["order.pending", "order.processing"]:
                self._set_pending()
                _logger.info(
                    "Pagar.me: Transaction %s marked as pending via webhook",
                    self.reference,
                )
            else:
                _logger.warning(
                    "Pagar.me: Unknown webhook event type %s for transaction %s",
                    event_type,
                    self.reference,
                )
        else:
            # Direct order data format (for tests and direct API responses)
            order_status = notification_data.get("status")
            charges = notification_data.get("charges", [])

            paid_status = order_status == "paid" or (
                charges and charges[0].get("status") == "paid"
            )
            if paid_status:
                # Check if manual capture is enabled like payment_demo
                manual_capture = notification_data.get("manual_capture", False)
                if self.provider_id.capture_manually and not manual_capture:
                    self._set_authorized()
                    _logger.info(
                        "Pagar.me: Transaction %s marked as authorized",
                        self.reference,
                    )
                else:
                    self._set_done()
                    _logger.info(
                        "Pagar.me: Transaction %s marked as done", self.reference
                    )
            elif order_status == "failed" or (
                charges and charges[0].get("status") == "failed"
            ):
                error_message = "Payment failed"
                if charges:
                    gateway_reason = (
                        charges[0]
                        .get("last_transaction", {})
                        .get("gateway_response", {})
                        .get("reason")
                    )
                    if gateway_reason:
                        error_message = gateway_reason
                self._set_error(error_message)
                _logger.error(
                    "Pagar.me: Transaction %s failed: %s",
                    self.reference,
                    error_message,
                )
            elif order_status == "canceled" or (
                charges and charges[0].get("status") == "canceled"
            ):
                self._set_canceled()
                _logger.info(
                    "Pagar.me: Transaction %s marked as canceled", self.reference
                )
            elif order_status in ["pending", "processing"] or (
                charges and charges[0].get("status") in ["pending", "processing"]
            ):
                self._set_pending()
                _logger.info(
                    "Pagar.me: Transaction %s marked as pending", self.reference
                )
            else:
                _logger.warning(
                    "Pagar.me: Unknown order status %s for transaction %s",
                    order_status,
                    self.reference,
                )

    @api.model
    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Find the transaction based on the notification data."""
        if provider_code != "pagarme":
            return super()._get_tx_from_notification_data(
                provider_code, notification_data
            )

        # Extract order ID from webhook data
        event_data = notification_data.get("data", {})
        order_id = event_data.get("id") or notification_data.get("id")

        # Also try to get reference directly from notification data
        reference = notification_data.get("reference")

        if order_id:
            # Find transaction by Pagar.me order ID
            tx = self.search([("provider_reference", "=", order_id)], limit=1)
            if tx:
                return tx

        if reference:
            # Find transaction by reference
            tx = self.search([("reference", "=", reference)], limit=1)
            if tx:
                return tx

        # No transaction found
        _logger.error(
            "Pagar.me: No transaction found for order_id=%s reference=%s",
            order_id,
            reference,
        )
        return self.env["payment.transaction"]
