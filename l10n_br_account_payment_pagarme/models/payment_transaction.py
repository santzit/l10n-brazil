# Copyright 2024 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..constants.pagarme_api import (
    PAGARME_PAYMENT_METHODS,
    PAGARME_TRANSACTION_STATUS,
)

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    """Payment Transaction for Pagar.me integration."""
    
    _inherit = "payment.transaction"

    # Pagar.me specific fields
    pagarme_transaction_id = fields.Char(
        string="Pagar.me Transaction ID",
        readonly=True,
        help="Pagar.me transaction identifier"
    )

    pagarme_charge_id = fields.Char(
        string="Pagar.me Charge ID", 
        readonly=True,
        help="Pagar.me charge identifier"
    )

    pagarme_payment_method = fields.Selection(
        selection=PAGARME_PAYMENT_METHODS,
        string="Payment Method",
        help="Payment method used in Pagar.me"
    )

    # Credit Card specific fields
    pagarme_card_id = fields.Char(
        string="Card ID",
        readonly=True,
        help="Pagar.me card identifier"
    )

    pagarme_installments = fields.Integer(
        string="Installments",
        default=1,
        help="Number of installments for credit card payments"
    )

    pagarme_card_brand = fields.Char(
        string="Card Brand",
        readonly=True,
        help="Credit card brand"
    )

    pagarme_card_last_digits = fields.Char(
        string="Card Last 4 Digits",
        readonly=True,
        help="Last 4 digits of the credit card"
    )

    # Boleto specific fields  
    pagarme_boleto_url = fields.Char(
        string="Boleto URL",
        readonly=True,
        help="URL to access the boleto"
    )

    pagarme_boleto_barcode = fields.Char(
        string="Boleto Barcode",
        readonly=True,
        help="Boleto barcode number"
    )

    pagarme_boleto_due_date = fields.Datetime(
        string="Boleto Due Date",
        readonly=True,
        help="Boleto payment due date"
    )

    # PIX specific fields
    pagarme_pix_qr_code = fields.Text(
        string="PIX QR Code",
        readonly=True,
        help="PIX QR code for payment"
    )

    pagarme_pix_qr_code_url = fields.Char(
        string="PIX QR Code URL",
        readonly=True, 
        help="URL to access PIX QR code image"
    )

    pagarme_pix_expiration_date = fields.Datetime(
        string="PIX Expiration Date",
        readonly=True,
        help="PIX payment expiration date"
    )

    # Fraud analysis fields
    pagarme_fraud_status = fields.Char(
        string="Fraud Status",
        readonly=True,
        help="Anti-fraud analysis status"
    )

    pagarme_fraud_score = fields.Float(
        string="Fraud Score",
        readonly=True,
        help="Anti-fraud score (0-100)"
    )

    # Additional fields
    pagarme_gateway_response = fields.Text(
        string="Gateway Response",
        readonly=True,
        help="Complete response from Pagar.me gateway"
    )

    pagarme_acquirer_message = fields.Char(
        string="Acquirer Message",
        readonly=True,
        help="Message from the acquirer"
    )

    pagarme_acquirer_code = fields.Char(
        string="Acquirer Code",
        readonly=True,
        help="Response code from the acquirer"
    )

    def _get_specific_rendering_values(self, processing_values):
        """Override to provide Pagar.me specific rendering values."""
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != "pagarme":
            return res

        # Add Pagar.me specific values
        pagarme_values = {
            "pagarme_public_key": self.provider_id.pagarme_public_key,
            "pagarme_transaction_id": self.pagarme_transaction_id,
            "pagarme_payment_method": self.pagarme_payment_method,
            "pagarme_max_installments": self.provider_id.pagarme_max_installments,
            "pagarme_min_installment_amount": self.provider_id.pagarme_min_installment_amount,
            "pagarme_enable_credit_card": self.provider_id.pagarme_enable_credit_card,
            "pagarme_enable_debit_card": self.provider_id.pagarme_enable_debit_card,
            "pagarme_enable_boleto": self.provider_id.pagarme_enable_boleto,
            "pagarme_enable_pix": self.provider_id.pagarme_enable_pix,
        }
        
        res.update(pagarme_values)
        return res

    def _pagarme_create_transaction_request(self):
        """Create transaction request data for Pagar.me API."""
        # Base transaction data
        request_data = {
            "amount": int(self.amount * 100),  # Convert to cents
            "currency": self.currency_id.name.lower(),
            "payment_method": self.pagarme_payment_method,
            "customer": self._pagarme_prepare_customer_data(),
            "metadata": {
                "odoo_transaction_id": self.id,
                "odoo_reference": self.reference,
                "order_id": self.source_transaction_id.id if self.source_transaction_id else None,
            }
        }

        # Add payment method specific data
        if self.pagarme_payment_method == "credit_card":
            request_data.update(self._pagarme_prepare_credit_card_data())
        elif self.pagarme_payment_method == "boleto":
            request_data.update(self._pagarme_prepare_boleto_data()) 
        elif self.pagarme_payment_method == "pix":
            request_data.update(self._pagarme_prepare_pix_data())

        # Add anti-fraud data if enabled
        if self.provider_id.pagarme_antifraud_enabled:
            request_data["antifraud"] = self._pagarme_prepare_antifraud_data()

        return request_data

    def _pagarme_prepare_customer_data(self):
        """Prepare customer data for Pagar.me API."""
        partner = self.partner_id
        
        customer_data = {
            "name": partner.name,
            "email": partner.email or "",
            "type": "individual" if partner.is_company == False else "corporation",
        }

        # Add document (CPF/CNPJ)
        if partner.cnpj_cpf:
            doc_type = "cnpj" if partner.is_company else "cpf"
            customer_data["document"] = partner.cnpj_cpf.replace(".", "").replace("-", "").replace("/", "")
            customer_data["document_type"] = doc_type

        # Add phone
        if partner.phone:
            # Clean phone number
            phone = partner.phone.replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
            customer_data["phones"] = {
                "home_phone": {
                    "country_code": "55",
                    "area_code": phone[2:4] if len(phone) >= 10 else "11",
                    "number": phone[4:] if len(phone) >= 10 else phone,
                }
            }

        # Add address
        if partner.street:
            customer_data["address"] = {
                "line_1": partner.street,
                "line_2": partner.street2 or "",
                "zip_code": partner.zip.replace("-", "") if partner.zip else "",
                "city": partner.city or "",
                "state": partner.state_id.code if partner.state_id else "",
                "country": partner.country_id.code if partner.country_id else "BR",
            }

        return customer_data

    def _pagarme_prepare_credit_card_data(self):
        """Prepare credit card payment data."""
        return {
            "credit_card": {
                "installments": self.pagarme_installments,
                "statement_descriptor": self.provider_id.name[:22],  # Max 22 chars
                "capture": self.provider_id.pagarme_capture_method == "automatic",
            }
        }

    def _pagarme_prepare_boleto_data(self):
        """Prepare boleto payment data."""
        due_date = datetime.now() + timedelta(days=self.provider_id.pagarme_boleto_expiration_days)
        
        return {
            "boleto": {
                "due_at": due_date.isoformat(),
                "instructions": self.provider_id.pagarme_boleto_instructions or "Pay only with this boleto",
                "document_number": self.reference,
            }
        }

    def _pagarme_prepare_pix_data(self):
        """Prepare PIX payment data."""
        expiration_date = datetime.now() + timedelta(minutes=self.provider_id.pagarme_pix_expiration_minutes)
        
        return {
            "pix": {
                "expires_at": expiration_date.isoformat(),
                "expires_in": self.provider_id.pagarme_pix_expiration_minutes * 60,  # Convert to seconds
            }
        }

    def _pagarme_prepare_antifraud_data(self):
        """Prepare anti-fraud analysis data."""
        return {
            "type": self.provider_id.pagarme_antifraud_rule,
            "clearsale": {
                "custom_sla": 60,  # 60 minutes for analysis
            }
        }

    def _pagarme_create_transaction(self):
        """Create transaction in Pagar.me."""
        request_data = self._pagarme_create_transaction_request()
        
        try:
            response = self.provider_id._pagarme_make_request("transactions", request_data)
            self._pagarme_process_transaction_response(response)
            return response
        except Exception as e:
            _logger.error("Error creating Pagar.me transaction: %s", str(e))
            self._set_error("Error creating transaction: %s" % str(e))
            raise

    def _pagarme_process_transaction_response(self, response):
        """Process Pagar.me transaction response."""
        if not response:
            return

        # Update transaction fields
        self.pagarme_transaction_id = response.get("id")
        self.pagarme_gateway_response = json.dumps(response, indent=2)
        
        # Update status
        pagarme_status = response.get("status")
        if pagarme_status:
            odoo_status = PAGARME_TRANSACTION_STATUS.get(pagarme_status, "pending")
            self._set_done() if odoo_status == "done" else self._set_pending()

        # Process payment method specific data
        charges = response.get("charges", [])
        if charges:
            charge = charges[0]  # Get first charge
            self.pagarme_charge_id = charge.get("id")
            
            # Process charge data based on payment method
            last_transaction = charge.get("last_transaction", {})
            payment_method = last_transaction.get("transaction_type")
            
            if payment_method == "credit_card":
                self._pagarme_process_credit_card_response(last_transaction)
            elif payment_method == "boleto":
                self._pagarme_process_boleto_response(last_transaction) 
            elif payment_method == "pix":
                self._pagarme_process_pix_response(last_transaction)

        # Process anti-fraud data
        antifraud = response.get("antifraud")
        if antifraud:
            self.pagarme_fraud_status = antifraud.get("status")
            self.pagarme_fraud_score = antifraud.get("score")

    def _pagarme_process_credit_card_response(self, transaction_data):
        """Process credit card transaction response."""
        card_data = transaction_data.get("card", {})
        self.pagarme_card_brand = card_data.get("brand")
        self.pagarme_card_last_digits = card_data.get("last_four_digits")
        self.pagarme_installments = transaction_data.get("installments", 1)
        
        # Acquirer information
        gateway_response = transaction_data.get("gateway_response", {})
        self.pagarme_acquirer_code = gateway_response.get("code")
        self.pagarme_acquirer_message = gateway_response.get("message")

    def _pagarme_process_boleto_response(self, transaction_data):
        """Process boleto transaction response."""
        self.pagarme_boleto_url = transaction_data.get("url")
        self.pagarme_boleto_barcode = transaction_data.get("barcode")
        
        due_at = transaction_data.get("due_at")
        if due_at:
            self.pagarme_boleto_due_date = datetime.fromisoformat(due_at.replace("Z", "+00:00"))

    def _pagarme_process_pix_response(self, transaction_data):
        """Process PIX transaction response."""
        pix_data = transaction_data.get("pix", {})
        self.pagarme_pix_qr_code = pix_data.get("qr_code")
        self.pagarme_pix_qr_code_url = pix_data.get("qr_code_url")
        
        expires_at = transaction_data.get("expires_at")
        if expires_at:
            self.pagarme_pix_expiration_date = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))

    @api.model
    def _pagarme_webhook_process(self, data):
        """Process webhook data from Pagar.me."""
        event_type = data.get("type")
        transaction_data = data.get("data")
        
        if not transaction_data:
            return

        # Find transaction by Pagar.me ID
        pagarme_id = transaction_data.get("id")
        transaction = self.search([("pagarme_transaction_id", "=", pagarme_id)], limit=1)
        
        if not transaction:
            _logger.warning("Webhook received for unknown transaction: %s", pagarme_id)
            return

        # Update transaction status based on event
        if event_type in ["transaction.paid", "charge.paid"]:
            transaction._set_done()
        elif event_type in ["transaction.refused", "transaction.chargedback", "charge.failed"]:
            transaction._set_canceled()
        elif event_type in ["transaction.refunded", "transaction.pending_refund"]:
            transaction._set_canceled()  # Or create refund transaction

        # Update transaction data
        transaction._pagarme_process_transaction_response(transaction_data)
        
        _logger.info("Processed webhook for transaction %s: %s", transaction.reference, event_type)