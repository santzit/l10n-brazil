# Copyright 2024 KMEE INFORMATICA LTDA  
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
import requests

from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    #=== BUSINESS METHODS ===#

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return Pagar.me-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'pagarme':
            return res

        _logger.info("=== PAGAR.ME TRANSACTION _get_specific_processing_values CALLED ===")
        _logger.info("Transaction: %s (ID: %s, state: %s)", self.reference, self.id, self.state)

        # Generate access token using standard payment utilities
        access_token = payment_utils.generate_access_token(
            self.partner_id.id, self.amount, self.currency_id.id
        )
            
        # Provide transaction context AND processing configuration for transparent checkout
        pagarme_values = {
            # Essential transaction context that template needs
            'reference': self.reference,
            'provider_id': self.provider_id.id,
            'access_token': access_token,
            'amount': self.amount,
            'currency': self.currency_id,
            'tx': self,
            # Configuration values for JavaScript processing 
            'api_key': self.provider_id.pagarme_api_key,
            'encryption_key': self.provider_id.pagarme_encryption_key,
        }
        
        _logger.info("Providing processing values with transaction context: reference=%s, provider_id=%s, access_token=%s...", 
                    pagarme_values['reference'], 
                    pagarme_values['provider_id'], 
                    pagarme_values['access_token'][:20] + "..." if pagarme_values['access_token'] else "None")
        
        return {**res, **pagarme_values}

    def _handle_feedback_data(self, provider_code, feedback_data):
        """Handle feedback data from transparent checkout or webhooks."""
        if provider_code != "pagarme":
            return super()._handle_feedback_data(provider_code, feedback_data)
            
        _logger.info("Pagar.me: Processing feedback data for transaction %s", self.reference)
        
        # Update provider reference if available
        if feedback_data.get("id"):
            self.provider_reference = str(feedback_data["id"])
            
        # Process notification data to update transaction state
        self._process_notification_data(feedback_data)

    def _send_payment_request(self):
        """Prepare payment request data for Pagar.me API (called by controllers in transparent checkout)."""
        if self.provider_code != "pagarme":
            return super()._send_payment_request()
            
        _logger.info("Pagar.me: Preparing payment request for transaction %s", self.reference)
        
        # Prepare customer data inline
        partner = self.partner_id
        document = partner.cnpj_cpf or ""
        clean_document = document.replace(".", "").replace("-", "").replace("/", "")
        
        if len(clean_document) == 11:
            document_type = "cpf"
            customer_type = "individual"
        elif len(clean_document) == 14:
            document_type = "cnpj"
            customer_type = "company"
        else:
            raise UserError(_("Invalid document format for partner %s") % partner.name)

        # Prepare phone number
        phone = partner.phone or partner.mobile or ""
        clean_phone = "".join(filter(str.isdigit, phone))
        
        if len(clean_phone) >= 10:
            area_code = clean_phone[-10:-8] if len(clean_phone) >= 10 else "11"
            number = clean_phone[-8:] if len(clean_phone) >= 8 else "99999999"
        else:
            area_code = "11"
            number = "99999999"

        customer_data = {
            "name": partner.name or "",
            "email": partner.email or "",
            "document": clean_document,
            "document_type": document_type,
            "type": customer_type,
            "phones": {
                "home_phone": {
                    "country_code": "55",
                    "area_code": area_code,
                    "number": number,
                }
            },
            "address": {
                "street": partner.street or "",
                "street_number": partner.street2 or "S/N",
                "neighborhood": partner.city or "",
                "city": partner.city or "",
                "state": partner.state_id.code if partner.state_id else "",
                "zip_code": partner.zip.replace("-", "") if partner.zip else "",
                "country": partner.country_id.code if partner.country_id else "BR",
                "complement": partner.street2 or "",
            }
        }
        
        # Prepare order data inline  
        items = []
        
        # If we have sale order, use order lines
        if hasattr(self, 'sale_order_ids') and self.sale_order_ids:
            for order in self.sale_order_ids:
                for line in order.order_line:
                    items.append({
                        "id": str(line.id),
                        "title": line.name or line.product_id.name,
                        "unit_price": int(line.price_unit * 100),  # Convert to cents
                        "quantity": int(line.product_uom_qty),
                        "tangible": True,
                    })
        else:
            # Fallback to generic item
            items.append({
                "id": "1",
                "title": f"Payment - {self.reference}",
                "unit_price": int(self.amount * 100),  # Convert to cents
                "quantity": 1,
                "tangible": False,
            })

        order_data = {
            "amount": int(self.amount * 100),  # Amount in cents
            "currency": "BRL",
            "items": items,
        }
        
        # Create transaction payload
        transaction_data = {
            **order_data,
            "customer": customer_data,
            "metadata": {
                "odoo_reference": self.reference,
                "odoo_partner_id": str(self.partner_id.id),
                "odoo_transaction_id": str(self.id),
                "integration": "odoo_payment",
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