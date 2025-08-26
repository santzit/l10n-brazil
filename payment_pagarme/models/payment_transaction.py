# Copyright 2024 KMEE INFORMATICA LTDA  
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
import requests

from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    #=== BUSINESS METHODS ===#

    def _get_specific_processing_values(self, processing_values):
        """Return Pagar.me-specific processing values for inline form."""
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != "pagarme":
            return res

        # Pagar.me specific values for inline form
        pagarme_values = {
            "api_key": self.provider_id.pagarme_api_key,
            "encryption_key": self.provider_id.pagarme_encryption_key,
            "amount": int(self.amount * 100),  # Convert to cents
            "currency": self.currency_id.name,
        }
        
        return {**res, **pagarme_values}

    def _send_payment_request(self):
        """Send the payment request to Pagar.me."""
        if self.provider_code != "pagarme":
            return super()._send_payment_request()
            
        _logger.info("Pagar.me: Sending payment request for transaction %s", self.reference)
        
        # Prepare customer data
        customer_data = self.provider_id._prepare_pagarme_customer_data(self.partner_id)
        
        # Prepare order data  
        order_data = self.provider_id._prepare_pagarme_order_data({
            'amount': self.amount,
            'reference': self.reference,
            'sale_order_ids': self.sale_order_ids.ids if hasattr(self, 'sale_order_ids') else []
        })
        
        # Create transaction payload
        transaction_data = {
            **order_data,
            "customer": customer_data,
            "metadata": {
                "odoo_reference": self.reference,
                "odoo_partner_id": str(self.partner_id.id),
                "odoo_transaction_id": str(self.id),
                "integration": "odoo_l10n_br",
            },
            "postback_url": f"{self.provider_id.get_base_url()}/payment/pagarme/webhook",
        }
        
        return transaction_data

    def _send_refund_request(self, amount_to_refund=None):
        """Send refund request to Pagar.me."""
        if self.provider_code != "pagarme":
            return super()._send_refund_request(amount_to_refund)
            
        if not self.provider_reference:
            raise UserError(_("Cannot refund transaction without Pagar.me transaction ID"))
            
        # Prepare refund data
        refund_amount = amount_to_refund or self.amount
        refund_data = {
            "amount": int(refund_amount * 100),  # Convert to cents
            "metadata": {
                "odoo_refund_reference": f"refund_{self.reference}",
                "odoo_transaction_id": str(self.id),
            }
        }
        
        # Send refund request to Pagar.me
        endpoint = f"transactions/{self.provider_reference}/refunds"
        response = self.provider_id._pagarme_make_request(endpoint, refund_data)
        
        # Process refund response
        if response.get("status") == "success":
            self._set_canceled()
            return response
        else:
            raise UserError(_("Refund failed: %s") % response.get("message", "Unknown error"))

    def _send_capture_request(self):
        """Send capture request to Pagar.me (for authorized transactions)."""
        if self.provider_code != "pagarme":
            return super()._send_capture_request()
            
        if not self.provider_reference:
            raise UserError(_("Cannot capture transaction without Pagar.me transaction ID"))
            
        endpoint = f"transactions/{self.provider_reference}/capture"
        response = self.provider_id._pagarme_make_request(endpoint, {})
        
        if response.get("status") == "paid":
            self._set_done()
        
        return response

    def _send_void_request(self):
        """Send void request to Pagar.me (cancel authorized transaction)."""
        if self.provider_code != "pagarme":
            return super()._send_void_request()
            
        if not self.provider_reference:
            raise UserError(_("Cannot void transaction without Pagar.me transaction ID"))
            
        endpoint = f"transactions/{self.provider_reference}/cancel"
        response = self.provider_id._pagarme_make_request(endpoint, {})
        
        if response.get("status") in ["canceled", "failed"]:
            self._set_canceled()
        
        return response

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Get transaction from Pagar.me notification data."""
        if provider_code != "pagarme":
            return super()._get_tx_from_notification_data(provider_code, notification_data)
            
        reference = notification_data.get("metadata", {}).get("odoo_reference")
        if not reference:
            raise ValidationError(_("Pagar.me: missing transaction reference in notification data"))
            
        tx = self.search([("reference", "=", reference), ("provider_code", "=", "pagarme")])
        if not tx:
            raise ValidationError(_("Pagar.me: no transaction found for reference %s") % reference)
        if len(tx) > 1:
            raise ValidationError(_("Pagar.me: multiple transactions found for reference %s") % reference)
            
        return tx

    def _process_notification_data(self, notification_data):
        """Process notification data from Pagar.me."""
        if self.provider_code != "pagarme":
            return super()._process_notification_data(notification_data)
            
        _logger.info("Pagar.me: Processing notification for transaction %s", self.reference)
        
        # Update provider reference if available
        if notification_data.get("id"):
            self.provider_reference = str(notification_data["id"])
            
        # Handle the notification based on transaction status
        transaction_status = notification_data.get("status", "").lower()
        
        if transaction_status == "paid":
            self._set_done()
        elif transaction_status in ["refused", "failed"]:
            self._set_canceled()
        elif transaction_status == "pending":
            self._set_pending()
        elif transaction_status == "authorized":
            self._set_authorized()
        elif transaction_status in ["refunded", "partial_refunded"]:
            self._set_canceled()
        else:
            _logger.warning("Unhandled Pagar.me transaction status: %s", transaction_status)