# Copyright 2024 OCA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    pagarme_token = fields.Char(
        string="Pagar.me Token",
        help="Token received from Pagar.me tokenization",
        readonly=True,
    )
    pagarme_order_id = fields.Char(
        string="Pagar.me Order ID",
        help="Order ID from Pagar.me",
        readonly=True,
    )
    pagarme_charge_id = fields.Char(
        string="Pagar.me Charge ID", 
        help="Charge ID from Pagar.me",
        readonly=True,
    )

    def _get_specific_rendering_values(self, processing_values):
        """Return Pagar.me-specific rendering values."""
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider != "pagarme":
            return res

        rendering_values = self.acquirer_id.pagarme_form_generate_values(processing_values)
        return rendering_values

    def _pagarme_create_order(self, token_data):
        """Create an order in Pagar.me using the token."""
        self.ensure_one()
        
        # Prepare order data
        order_data = {
            "amount": int(self.amount * 100),  # Convert to cents
            "currency": self.currency_id.name,
            "payments": [{
                "payment_method": "credit_card",
                "amount": int(self.amount * 100),
                "credit_card": {
                    "card_token": self.pagarme_token,
                    "statement_descriptor": f"Pedido {self.reference}",
                }
            }],
            "customer": {
                "name": self.partner_name or "",
                "email": self.partner_email or "",
                "document": getattr(self.partner_id, "vat", "") or "",
                "type": "individual",
            },
            "metadata": {
                "odoo_reference": self.reference,
                "odoo_transaction_id": str(self.id),
            }
        }

        # Add phone if available
        if self.partner_phone:
            order_data["customer"]["phones"] = {
                "mobile_phone": {
                    "country_code": "55",
                    "area_code": self.partner_phone[:2] if len(self.partner_phone) >= 11 else "11",
                    "number": self.partner_phone[2:] if len(self.partner_phone) >= 11 else self.partner_phone,
                }
            }

        try:
            result = self.acquirer_id._pagarme_make_request("/orders", order_data)
            self.pagarme_order_id = result.get("id")
            
            # Get charge information
            charges = result.get("charges", [])
            if charges:
                self.pagarme_charge_id = charges[0].get("id")
                
            return result
        except Exception as e:
            _logger.error("Failed to create Pagar.me order: %s", e)
            raise ValidationError(_("Failed to process payment: %s") % str(e))

    def _pagarme_process_webhook_data(self, data):
        """Process webhook data from Pagar.me."""
        self.ensure_one()
        
        status = data.get("status")
        charge_status = None
        
        # Check if it's an order webhook
        if "charges" in data:
            charges = data.get("charges", [])
            if charges:
                charge_status = charges[0].get("status")
        
        # Map Pagar.me status to Odoo status
        if status == "paid" or charge_status == "paid":
            self._set_done()
        elif status == "failed" or charge_status == "failed":
            self._set_error(_("Payment failed"))
        elif status == "canceled" or charge_status == "canceled":
            self._set_canceled()
        elif status == "pending" or charge_status == "pending":
            self._set_pending()
        else:
            _logger.warning("Unknown Pagar.me status: %s", status)

    @api.model
    def _pagarme_form_get_tx_from_data(self, data):
        """Find transaction from webhook data."""
        reference = data.get("metadata", {}).get("odoo_reference")
        if reference:
            tx = self.search([("reference", "=", reference)], limit=1)
            if tx:
                return tx
        
        # Fallback to order_id or charge_id
        order_id = data.get("id")
        charge_id = None
        if "charges" in data and data["charges"]:
            charge_id = data["charges"][0].get("id")
            
        if order_id:
            tx = self.search([("pagarme_order_id", "=", order_id)], limit=1)
            if tx:
                return tx
                
        if charge_id:
            tx = self.search([("pagarme_charge_id", "=", charge_id)], limit=1)
            if tx:
                return tx
                
        raise ValidationError(_("Pagar.me transaction not found"))

    def _process_notification_data(self, notification_data):
        """Process notification data.""" 
        if self.provider != "pagarme":
            return super()._process_notification_data(notification_data)
        
        self._pagarme_process_webhook_data(notification_data)
        return notification_data