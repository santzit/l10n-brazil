# Copyright 2024 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..constants.pagarme_api import PAGARME_PAYMENT_METHODS

_logger = logging.getLogger(__name__)


class AccountPaymentOrder(models.Model):
    """Account Payment Order integration with Pagar.me."""
    
    _inherit = "account.payment.order"

    # Pagar.me specific fields
    pagarme_processor = fields.Boolean(
        string="Pagar.me Processor",
        compute="_compute_pagarme_processor",
        help="Indicates if this payment order uses Pagar.me processor"
    )

    pagarme_batch_id = fields.Char(
        string="Pagar.me Batch ID",
        readonly=True,
        help="Pagar.me batch identifier for bulk payments"
    )

    pagarme_batch_status = fields.Char(
        string="Batch Status",
        readonly=True,
        help="Status of the Pagar.me batch"
    )

    pagarme_payment_method = fields.Selection(
        selection=PAGARME_PAYMENT_METHODS,
        string="Default Payment Method",
        help="Default payment method for this order"
    )

    pagarme_split_rules = fields.Text(
        string="Split Rules",
        help="JSON configuration for payment split rules"
    )

    @api.depends("payment_mode_id", "payment_mode_id.cnab_config_id")
    def _compute_pagarme_processor(self):
        """Compute if this order uses Pagar.me processor."""
        for order in self:
            order.pagarme_processor = (
                order.payment_mode_id and
                order.payment_mode_id.cnab_config_id and
                order.payment_mode_id.cnab_config_id.cnab_processor == "pagarme"
            )

    def generate_payment_file(self):
        """Override to handle Pagar.me payment generation."""
        self.ensure_one()
        
        # Check if this is a Pagar.me order
        if not self.pagarme_processor:
            return super().generate_payment_file()

        # Validate Pagar.me configuration
        self._pagarme_validate_configuration()

        # Generate Pagar.me payments
        return self._pagarme_generate_payments()

    def _pagarme_validate_configuration(self):
        """Validate Pagar.me configuration before processing."""
        cnab_config = self.payment_mode_id.cnab_config_id
        
        if not cnab_config.pagarme_api_key:
            raise UserError(_("Pagar.me API key is not configured"))
            
        if not cnab_config.pagarme_public_key:
            raise UserError(_("Pagar.me public key is not configured"))
            
        # Validate payment method
        if not self.pagarme_payment_method:
            raise UserError(_("Payment method must be specified for Pagar.me orders"))

    def _pagarme_generate_payments(self):
        """Generate payments using Pagar.me API."""
        cnab_config = self.payment_mode_id.cnab_config_id
        payments_data = []
        
        # Process each payment line
        for line in self.payment_line_ids:
            payment_data = self._pagarme_prepare_payment_data(line)
            payments_data.append(payment_data)

        # Create batch payment if multiple payments
        if len(payments_data) > 1:
            return self._pagarme_create_batch_payment(payments_data)
        elif len(payments_data) == 1:
            return self._pagarme_create_single_payment(payments_data[0])
        else:
            raise UserError(_("No payment lines to process"))

    def _pagarme_prepare_payment_data(self, payment_line):
        """Prepare payment data for a single payment line."""
        move_line = payment_line.move_line_id
        partner = payment_line.partner_id
        
        payment_data = {
            "amount": int(payment_line.amount_currency * 100),  # Convert to cents
            "currency": payment_line.currency_id.name.lower(),
            "payment_method": self.pagarme_payment_method,
            "description": f"Payment for {move_line.move_id.name}",
            "reference": payment_line.name,
            "customer": self._pagarme_prepare_customer_data(partner),
            "metadata": {
                "odoo_payment_line_id": payment_line.id,
                "odoo_move_id": move_line.move_id.id,
                "odoo_partner_id": partner.id,
            }
        }

        # Add payment method specific configuration
        if self.pagarme_payment_method == "boleto":
            payment_data.update(self._pagarme_prepare_boleto_config(payment_line))
        elif self.pagarme_payment_method == "pix":
            payment_data.update(self._pagarme_prepare_pix_config(payment_line))

        # Add split rules if configured
        if self.pagarme_split_rules:
            try:
                split_rules = json.loads(self.pagarme_split_rules)
                payment_data["split"] = split_rules
            except json.JSONDecodeError:
                _logger.warning("Invalid split rules JSON for order %s", self.name)

        return payment_data

    def _pagarme_prepare_customer_data(self, partner):
        """Prepare customer data for Pagar.me API."""
        customer_data = {
            "name": partner.name,
            "email": partner.email or "",
            "type": "corporation" if partner.is_company else "individual",
        }

        # Add document (CPF/CNPJ)
        if partner.cnpj_cpf:
            doc_type = "cnpj" if partner.is_company else "cpf"
            clean_doc = partner.cnpj_cpf.replace(".", "").replace("-", "").replace("/", "")
            customer_data["document"] = clean_doc
            customer_data["document_type"] = doc_type

        # Add phone
        if partner.phone:
            phone = partner.phone.replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
            if len(phone) >= 10:
                customer_data["phones"] = {
                    "home_phone": {
                        "country_code": "55",
                        "area_code": phone[2:4],
                        "number": phone[4:],
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

    def _pagarme_prepare_boleto_config(self, payment_line):
        """Prepare boleto specific configuration."""
        cnab_config = self.payment_mode_id.cnab_config_id
        due_date = payment_line.date_maturity or fields.Date.today()
        
        return {
            "boleto": {
                "due_at": due_date.isoformat(),
                "instructions": cnab_config.pagarme_boleto_instructions or "Pay only with this boleto",
                "document_number": payment_line.name,
            }
        }

    def _pagarme_prepare_pix_config(self, payment_line):
        """Prepare PIX specific configuration."""
        cnab_config = self.payment_mode_id.cnab_config_id
        
        return {
            "pix": {
                "expires_in": cnab_config.pagarme_pix_expiration_minutes * 60,  # Convert to seconds
            }
        }

    def _pagarme_create_single_payment(self, payment_data):
        """Create a single payment in Pagar.me."""
        cnab_config = self.payment_mode_id.cnab_config_id
        
        try:
            # Create transaction using the provider's API method
            response = cnab_config._pagarme_make_request("transactions", payment_data)
            
            # Process response
            self._pagarme_process_payment_response(response)
            
            # Generate file content (JSON format)
            file_content = json.dumps({
                "batch_id": response.get("id"),
                "status": "created",
                "payments": [response],
                "created_at": fields.Datetime.now().isoformat(),
            }, indent=2)
            
            filename = f"pagarme_payment_{self.name}_{fields.Date.today()}.json"
            
            return file_content.encode(), filename
            
        except Exception as e:
            _logger.error("Error creating Pagar.me payment: %s", str(e))
            raise UserError(_("Error creating payment: %s") % str(e))

    def _pagarme_create_batch_payment(self, payments_data):
        """Create batch payment in Pagar.me."""
        cnab_config = self.payment_mode_id.cnab_config_id
        
        batch_data = {
            "type": "bulk_anticipatable",
            "recipient_id": cnab_config.pagarme_recipient_id,
            "transactions": payments_data,
            "metadata": {
                "odoo_order_id": self.id,
                "odoo_order_name": self.name,
            }
        }
        
        try:
            # Create bulk anticipatable (batch payment)
            response = cnab_config._pagarme_make_request("bulk_anticipatables", batch_data)
            
            # Store batch information
            self.pagarme_batch_id = response.get("id")
            self.pagarme_batch_status = response.get("status")
            
            # Process each transaction response
            transactions = response.get("transactions", [])
            for i, transaction in enumerate(transactions):
                if i < len(self.payment_line_ids):
                    self._pagarme_process_line_response(self.payment_line_ids[i], transaction)
            
            # Generate file content
            file_content = json.dumps({
                "batch_id": self.pagarme_batch_id,
                "status": self.pagarme_batch_status,
                "payments": transactions,
                "created_at": fields.Datetime.now().isoformat(),
            }, indent=2)
            
            filename = f"pagarme_batch_{self.name}_{fields.Date.today()}.json"
            
            return file_content.encode(), filename
            
        except Exception as e:
            _logger.error("Error creating Pagar.me batch payment: %s", str(e))
            raise UserError(_("Error creating batch payment: %s") % str(e))

    def _pagarme_process_payment_response(self, response):
        """Process single payment response."""
        if self.payment_line_ids:
            self._pagarme_process_line_response(self.payment_line_ids[0], response)

    def _pagarme_process_line_response(self, payment_line, transaction_response):
        """Process payment response for a specific line."""
        # Store Pagar.me transaction ID in payment line
        payment_line.pagarme_transaction_id = transaction_response.get("id")
        
        # Update move line CNAB state
        if payment_line.move_line_id:
            payment_line.move_line_id.cnab_state = "exported"
            
        # Store additional information
        payment_line.pagarme_response = json.dumps(transaction_response, indent=2)

    def generated2uploaded(self):
        """Override to handle Pagar.me specific uploaded state."""
        result = super().generated2uploaded()
        
        if self.pagarme_processor:
            # Update payment lines state
            for payment_line in self.payment_line_ids:
                if payment_line.move_line_id:
                    payment_line.move_line_id.cnab_state = "sent"
                    
        return result

    def action_pagarme_check_status(self):
        """Action to check payment status in Pagar.me."""
        self.ensure_one()
        
        if not self.pagarme_processor:
            return
            
        cnab_config = self.payment_mode_id.cnab_config_id
        
        try:
            if self.pagarme_batch_id:
                # Check batch status
                response = cnab_config._pagarme_make_request(
                    f"bulk_anticipatables/{self.pagarme_batch_id}", 
                    method="GET"
                )
                self.pagarme_batch_status = response.get("status")
                
            # Check individual transactions
            for line in self.payment_line_ids:
                if hasattr(line, 'pagarme_transaction_id') and line.pagarme_transaction_id:
                    response = cnab_config._pagarme_make_request(
                        f"transactions/{line.pagarme_transaction_id}",
                        method="GET"
                    )
                    # Update line status based on response
                    status = response.get("status")
                    if status == "paid":
                        line.move_line_id.cnab_state = "reconciled"
                    elif status in ["refused", "chargedback"]:
                        line.move_line_id.cnab_state = "rejected"
                        
        except Exception as e:
            raise UserError(_("Error checking payment status: %s") % str(e))

    def _pagarme_webhook_update_order(self, webhook_data):
        """Update order based on webhook data."""
        transaction_id = webhook_data.get("data", {}).get("id")
        event_type = webhook_data.get("type")
        
        # Find payment line with this transaction ID
        payment_line = self.payment_line_ids.filtered(
            lambda l: hasattr(l, 'pagarme_transaction_id') and 
                     l.pagarme_transaction_id == transaction_id
        )
        
        if payment_line and payment_line.move_line_id:
            if event_type in ["transaction.paid", "charge.paid"]:
                payment_line.move_line_id.cnab_state = "reconciled"
            elif event_type in ["transaction.refused", "charge.failed"]:
                payment_line.move_line_id.cnab_state = "rejected"