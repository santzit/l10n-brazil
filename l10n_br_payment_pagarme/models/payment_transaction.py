# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import pprint

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    pagarme_charge_id = fields.Char(
        string="Pagar.me Charge ID",
        help="Charge ID from Pagar.me API",
        readonly=True
    )
    pagarme_card_token = fields.Char(
        string="Card Token",
        help="Tokenized card from frontend",
        readonly=True
    )

    def _get_specific_rendering_values(self, processing_values):
        """ Override to add Pagar.me-specific values to the checkout form. """
        res = super()._get_specific_rendering_values(processing_values)
        if self.acquirer_id.provider != "pagarme":
            return res

        pagarme_values = {
            "encryption_key": self.acquirer_id.pagarme_encryption_key,
            "api_url": self.acquirer_id._pagarme_get_api_url(),
        }
        return {**res, **pagarme_values}

    def _get_processing_info(self):
        """ Override to add Pagar.me processing information. """
        res = super()._get_processing_info()
        if self.acquirer_id.provider == "pagarme":
            res.update({
                "acquirer_name": "Pagar.me",
                "provider": "pagarme",
            })
        return res

    def _send_payment_request(self):
        """ Override to send payment request to Pagar.me. """
        super()._send_payment_request()
        if self.acquirer_id.provider != "pagarme":
            return

        if not self.pagarme_card_token:
            raise UserError(_("Card token is required for Pagar.me transactions"))

        # Prepare transaction data for Pagar.me API
        transaction_data = {
            "amount": self.amount,
            "reference": self.reference,
            "partner_name": self.partner_id.name,
            "partner_email": self.partner_id.email,
            "partner_vat": self.partner_id.vat or "",
            "card_token": self.pagarme_card_token,
        }

        # Add billing address if available
        if self.partner_id:
            partner = self.partner_id
            if partner.street:
                transaction_data["billing_address"] = {
                    "line_1": partner.street,
                    "line_2": partner.street2 or "",
                    "zip_code": partner.zip or "",
                    "city": partner.city or "",
                    "state": partner.state_id.code if partner.state_id else "",
                    "country": partner.country_id.code if partner.country_id else "BR",
                }

        try:
            # Create charge on Pagar.me
            charge_result = self.acquirer_id._pagarme_create_charge(transaction_data)
            self._handle_pagarme_response(charge_result)
            
        except Exception as error:
            _logger.exception("Error processing Pagar.me payment")
            self._set_error(
                "Pagar.me: " + _("Payment processing failed: %s") % str(error)
            )

    def _handle_pagarme_response(self, charge_data):
        """ Handle the response from Pagar.me charge creation. """
        self.ensure_one()
        
        _logger.info(
            "Received response from Pagar.me for transaction %s:\n%s",
            self.reference, pprint.pformat(charge_data)
        )

        # Store charge ID
        self.pagarme_charge_id = charge_data.get("id")
        
        # Map Pagar.me status to Odoo transaction state
        charge_status = charge_data.get("status")
        
        if charge_status == "paid":
            self._set_done()
        elif charge_status == "pending":
            self._set_pending()
        elif charge_status in ["failed", "canceled"]:
            error_msg = charge_data.get("gateway_response", {}).get("message", "Payment failed")
            self._set_error(f"Pagar.me: {error_msg}")
        else:
            _logger.warning(
                "Received unknown status from Pagar.me: %s for transaction %s",
                charge_status, self.reference
            )
            self._set_pending()

    def _process_webhook_data(self, webhook_data):
        """ Process webhook data from Pagar.me. """
        self.ensure_one()
        
        _logger.info(
            "Processing webhook data for transaction %s:\n%s",
            self.reference, pprint.pformat(webhook_data)
        )

        # Validate webhook data structure
        if not webhook_data.get("id") or webhook_data.get("id") != self.pagarme_charge_id:
            _logger.warning(
                "Webhook charge ID %s does not match transaction charge ID %s",
                webhook_data.get("id"), self.pagarme_charge_id
            )
            return

        # Update transaction status based on webhook
        charge_status = webhook_data.get("status")
        
        if charge_status == "paid" and self.state != "done":
            self._set_done()
        elif charge_status in ["failed", "canceled"] and self.state not in ["cancel", "error"]:
            error_msg = webhook_data.get("gateway_response", {}).get("message", "Payment failed")
            self._set_error(f"Pagar.me: {error_msg}")

    def _pagarme_tokenize_from_feedback_data(self, data):
        """ Extract and store card token from feedback data. """
        self.ensure_one()
        token = data.get("card_token")
        if token:
            self.pagarme_card_token = token
        else:
            raise ValidationError(_("Card token is missing from payment data"))