# Copyright 2024 KMEE INFORMATICA LTDA  
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    stone_pagarme_transaction_id = fields.Char(
        string="Stone/Pagar.me Transaction ID",
        help="The transaction ID returned by Stone/Pagar.me",
        readonly=True,
    )
    stone_pagarme_charge_id = fields.Char(
        string="Stone/Pagar.me Charge ID", 
        help="The charge ID returned by Stone/Pagar.me",
        readonly=True,
    )

    def _get_specific_rendering_values(self, processing_values):
        """Return Stone/Pagar.me-specific rendering values."""
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != "stone_pagarme":
            return res

        # Add Stone/Pagar.me specific values
        base_url = self.provider_id.get_base_url()
        stone_pagarme_values = {
            "encryption_key": self.provider_id.stone_pagarme_encryption_key,
            "return_url": f"{base_url}/payment/stone_pagarme/return",
            "webhook_url": self.provider_id.stone_pagarme_webhook_url,
            "reference": self.reference,
        }
        
        return {**res, **stone_pagarme_values}

    def _send_payment_request(self):
        """Send the payment request to Stone/Pagar.me."""
        if self.provider_code != "stone_pagarme":
            return super()._send_payment_request()
            
        _logger.info("Sending Stone/Pagar.me payment request for transaction %s", self.reference)
        
        # This method would typically be called from the frontend after card data collection
        # For now, we'll prepare the structure
        return self._stone_pagarme_create_transaction_request()

    def _stone_pagarme_create_transaction_request(self, card_data=None):
        """Create a transaction request to Stone/Pagar.me."""
        # Prepare customer data
        customer_data = self.provider_id._prepare_stone_pagarme_customer_data(self.partner_id)
        
        # Prepare order data  
        tx_values = {
            "amount": self.amount,
            "currency_id": self.currency_id.id,
            "reference": self.reference,
            "partner_id": self.partner_id.id,
        }
        
        # Add sale order if available
        if hasattr(self, "sale_order_ids") and self.sale_order_ids:
            tx_values["sale_order_ids"] = self.sale_order_ids.ids
            
        order_data = self.provider_id._prepare_stone_pagarme_order_data(tx_values)
        
        # Prepare payment data (card_data would come from frontend)
        if card_data:
            payment_data = self.provider_id._prepare_stone_pagarme_payment_data(tx_values, card_data)
        else:
            # For structure purposes - actual card data handled in frontend
            payment_data = {
                "payment_method": "credit_card",
                "credit_card": {
                    "installments": 1,
                    "statement_descriptor": "STONE PAGARME",
                }
            }

        # Create the complete transaction payload
        transaction_data = {
            "amount": order_data["amount"],
            "currency": order_data["currency"], 
            "payment": payment_data,
            "customer": customer_data,
            "items": order_data["items"],
            "metadata": {
                "odoo_reference": self.reference,
                "odoo_partner_id": str(self.partner_id.id),
                "odoo_transaction_id": str(self.id),
            },
        }
        
        return transaction_data

    def _stone_pagarme_process_transaction_response(self, response_data):
        """Process the response from Stone/Pagar.me transaction API."""
        if not response_data:
            raise UserError(_("Empty response from Stone/Pagar.me"))
            
        # Extract transaction information
        self.stone_pagarme_transaction_id = response_data.get("id")
        
        # Extract charge information if available
        charges = response_data.get("charges", [])
        if charges:
            charge = charges[0]  # Usually one charge per transaction
            self.stone_pagarme_charge_id = charge.get("id")
            
            # Update transaction status based on charge status
            charge_status = charge.get("status")
            if charge_status == "paid":
                self._set_done()
            elif charge_status == "pending":
                self._set_pending()
            elif charge_status in ["failed", "canceled"]:
                self._set_canceled()
            else:
                _logger.warning("Unknown Stone/Pagar.me charge status: %s", charge_status)
                
        # Store additional metadata
        if hasattr(self, "provider_reference"):
            self.provider_reference = self.stone_pagarme_transaction_id

    def _stone_pagarme_get_transaction_status(self):
        """Get transaction status from Stone/Pagar.me API."""
        if not self.stone_pagarme_transaction_id:
            raise UserError(_("No Stone/Pagar.me transaction ID found"))
            
        endpoint = f"orders/{self.stone_pagarme_transaction_id}"
        response = self.provider_id._stone_pagarme_make_request(endpoint, method="GET")
        
        return response

    @api.model
    def _stone_pagarme_form_get_tx_from_data(self, data):
        """Get transaction from Stone/Pagar.me webhook data."""
        reference = data.get("metadata", {}).get("odoo_reference")
        if not reference:
            raise ValidationError(_("Stone/Pagar.me: missing transaction reference in webhook data"))
            
        tx = self.search([("reference", "=", reference), ("provider_code", "=", "stone_pagarme")])
        if not tx:
            raise ValidationError(_("Stone/Pagar.me: no transaction found for reference %s") % reference)
        if len(tx) > 1:
            raise ValidationError(_("Stone/Pagar.me: multiple transactions found for reference %s") % reference)
            
        return tx

    def _stone_pagarme_form_validate(self, data):
        """Validate Stone/Pagar.me webhook data and update transaction status."""
        _logger.info("Validating Stone/Pagar.me webhook data for transaction %s", self.reference)
        
        # Update transaction with webhook data
        self._stone_pagarme_process_transaction_response(data)
        
        return True

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Override to handle Stone/Pagar.me notification data."""
        if provider_code != "stone_pagarme":
            return super()._get_tx_from_notification_data(provider_code, notification_data)
            
        return self._stone_pagarme_form_get_tx_from_data(notification_data)