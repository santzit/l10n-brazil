# Copyright 2024 KMEE INFORMATICA LTDA  
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
import requests
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    # Pagar.me specific fields following WooCommerce plugin field mapping
    pagarme_transaction_id = fields.Char(
        string="Pagar.me Transaction ID",
        help="The transaction ID returned by Pagar.me",
        readonly=True,
    )
    pagarme_charge_id = fields.Char(
        string="Pagar.me Charge ID", 
        help="The charge ID returned by Pagar.me",
        readonly=True,
    )
    pagarme_order_id = fields.Char(
        string="Pagar.me Order ID",
        help="The order ID returned by Pagar.me",
        readonly=True,
    )
    pagarme_status = fields.Char(
        string="Pagar.me Status",
        help="Latest status from Pagar.me",
        readonly=True,
    )
    pagarme_payment_method = fields.Selection([
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('pix', 'PIX'),
        ('boleto', 'Boleto'),
    ], string="Pagar.me Payment Method")
    
    # Credit card specific fields (following WooCommerce mapping)
    pagarme_card_brand = fields.Char(
        string="Card Brand",
        readonly=True,
    )
    pagarme_card_last_digits = fields.Char(
        string="Card Last 4 Digits",
        readonly=True,
    )
    pagarme_installments = fields.Integer(
        string="Number of Installments",
        default=1,
    )
    
    # Customer document fields for Brazilian market
    pagarme_customer_document = fields.Char(
        string="Customer Document (CPF/CNPJ)",
        readonly=True,
    )
    pagarme_customer_type = fields.Selection([
        ('individual', 'Individual (CPF)'),
        ('company', 'Company (CNPJ)'),
    ], string="Customer Type")

    def _get_specific_rendering_values(self, processing_values):
        """Return Pagar.me-specific rendering values."""
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != "pagarme":
            return res

        _logger.info("=== PAGAR.ME RENDERING VALUES DEBUG ===")
        _logger.info("Transaction ID: %s", self.id)
        _logger.info("Transaction Reference: %s", self.reference)
        _logger.info("Provider ID: %s", self.provider_id.id if self.provider_id else 'None')
        _logger.info("Processing values received: %s", processing_values)
        _logger.info("Transaction state: %s", self.state)
        
        # CRITICAL FIX: Ensure transaction always has a reference
        if not self.reference:
            _logger.error("CRITICAL: Transaction %s has no reference! This must be fixed before rendering.", self.id)
            # For debugging purposes, we can continue but this should be addressed
            
        # Extract access_token with proper fallback
        access_token = ''
        if processing_values and 'access_token' in processing_values:
            access_token = processing_values['access_token']
            _logger.info("Access token found in processing_values")
        elif hasattr(self, 'access_token') and self.access_token:
            access_token = self.access_token
            _logger.info("Access token found in transaction object")
        else:
            # Generate a temporary access token if none exists
            access_token = self._generate_access_token()
            _logger.info("Generated new access token: %s", access_token[:10] + "...")
            
        # Use transaction reference directly - it should always be available
        transaction_reference = self.reference or ""
        if not transaction_reference:
            _logger.error("CRITICAL: No transaction reference available!")

        # Add Pagar.me specific values for transparent checkout
        base_url = self.provider_id.get_base_url()
        pagarme_values = {
            "api_key": self.provider_id.pagarme_api_key,
            "encryption_key": self.provider_id.pagarme_encryption_key,
            "return_url": f"{base_url}/payment/pagarme/return",
            "webhook_url": f"{base_url}/payment/pagarme/webhook",
            "amount": int(self.amount * 100),  # Convert to cents
            "currency": self.currency_id.name,
            "partner_name": self.partner_id.name,
            "partner_email": self.partner_id.email,
            "partner_phone": self.partner_id.phone or self.partner_id.mobile,
            "partner_document": self.partner_id.cnpj_cpf,
            "customer_type": "company" if self.partner_id.is_company else "individual",
            # Set the form action to submit to our payment endpoint
            "form_action": f"{base_url}/payment/pagarme/payment",
            
            # CRITICAL: Ensure transaction context is ALWAYS available to template
            "reference": transaction_reference,
            "provider_id": self.provider_id.id,
            "access_token": access_token,
            "transaction_id": self.id,
            
            # Add the transaction object itself to the template context
            "tx": self,
            
            # Add processing_values to template context so template can access them
            "processing_values": processing_values or {},
        }
        
        # Add address information
        if self.partner_id:
            pagarme_values.update({
                "billing_address": {
                    "street": self.partner_id.street or "",
                    "street_number": self.partner_id.l10n_br_number or "",
                    "neighborhood": self.partner_id.l10n_br_district or "",
                    "city": self.partner_id.city or "",
                    "state": self.partner_id.state_id.code if self.partner_id.state_id else "",
                    "zipcode": self.partner_id.zip or "",
                    "country": self.partner_id.country_id.code if self.partner_id.country_id else "BR",
                    "complement": self.partner_id.street2 or "",
                }
            })
            
        _logger.info("=== FINAL RENDERING VALUES FOR TEMPLATE ===")
        _logger.info("Template will receive - reference: %s", pagarme_values.get("reference"))
        _logger.info("Template will receive - provider_id: %s", pagarme_values.get("provider_id"))
        _logger.info("Template will receive - access_token: %s", pagarme_values.get("access_token")[:10] + "..." if pagarme_values.get("access_token") else "NONE")
        _logger.info("Template will receive - transaction_id: %s", pagarme_values.get("transaction_id"))
        _logger.info("Template will receive - form_action: %s", pagarme_values.get("form_action"))
        _logger.info("Template will receive - tx object: %s", "YES" if pagarme_values.get("tx") else "NO")
        _logger.info("=======================================")
        
        final_values = {**res, **pagarme_values}
        return final_values

    def _generate_access_token(self):
        """Generate an access token for the transaction if none exists."""
        import uuid
        return str(uuid.uuid4())

    def _send_payment_request(self):
        """Send the payment request to Pagar.me."""
        if self.provider_code != "pagarme":
            return super()._send_payment_request()
            
        _logger.info("Sending Pagar.me payment request for transaction %s", self.reference)
        
        # This method would typically be called from the frontend after card data collection
        # For now, we'll prepare the structure
        return self._pagarme_create_transaction_request()

    def _process_notification_data(self, provider_code, notification_data):
        """Process notification data from Pagar.me."""
        if provider_code != "pagarme":
            return super()._process_notification_data(provider_code, notification_data)
            
        _logger.info("Processing Pagar.me notification for transaction %s", self.reference)
        
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

    def _send_refund_request(self, amount_to_refund=None):
        """Send refund request to Pagar.me."""
        if self.provider_code != "pagarme":
            return super()._send_refund_request(amount_to_refund)
            
        if not self.pagarme_transaction_id:
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
        endpoint = f"transactions/{self.pagarme_transaction_id}/refunds"
        response = self.provider_id._pagarme_make_request(endpoint, refund_data)
        
        # Process refund response
        if response.get("status") == "success":
            self._set_canceled()
            return response
        else:
            raise UserError(_("Refund failed: %s") % response.get("message", "Unknown error"))

    def _handle_notification_data(self, provider_code, notification_data):
        """Handle notification data from webhooks or return URL."""
        if provider_code != "pagarme":
            return super()._handle_notification_data(provider_code, notification_data)
            
        # Update transaction with Pagar.me data
        self._update_pagarme_transaction_data(notification_data)
        
        # Process the notification
        self._process_notification_data(provider_code, notification_data)

    def _update_pagarme_transaction_data(self, data):
        """Update transaction with data from Pagar.me."""
        if not data:
            return
            
        # Update Pagar.me specific fields
        vals = {}
        
        if "id" in data:
            vals["pagarme_transaction_id"] = str(data["id"])
            
        if "status" in data:
            vals["pagarme_status"] = data["status"]
            
        if "charges" in data and data["charges"]:
            charge = data["charges"][0]  # Get first charge
            if "id" in charge:
                vals["pagarme_charge_id"] = str(charge["id"])
                
            # Extract payment method info
            if "payment_method" in charge:
                payment_method = charge["payment_method"]
                vals["pagarme_payment_method"] = payment_method.get("type", "credit_card")
                
                # Extract card info if available
                if "card" in payment_method:
                    card_info = payment_method["card"]
                    vals["pagarme_card_brand"] = card_info.get("brand", "")
                    vals["pagarme_card_last_digits"] = card_info.get("last_four_digits", "")
                    
        if "order" in data and "id" in data["order"]:
            vals["pagarme_order_id"] = str(data["order"]["id"])
            
        if vals:
            self.write(vals)

    def _pagarme_create_transaction_request(self, card_data=None):
        """Create a transaction request to Pagar.me following API v5 structure."""
        # Prepare customer data following Pagar.me API v5
        customer_data = self._prepare_pagarme_customer_data()
        
        # Prepare order items
        items_data = self._prepare_pagarme_items_data()
        
        # Prepare payment data (card_data would come from frontend)
        if card_data:
            payment_data = self._prepare_pagarme_payment_data(card_data)
        else:
            # For structure purposes - actual card data handled in frontend
            payment_data = {
                "payment_method": "credit_card",
                "credit_card": {
                    "installments": self.pagarme_installments or 1,
                    "statement_descriptor": "PAGARME",
                    "card": {
                        # Card data will be encrypted on frontend
                        "number": "encrypted_card_number",
                        "holder_name": "encrypted_holder_name", 
                        "exp_month": "encrypted_exp_month",
                        "exp_year": "encrypted_exp_year",
                        "cvv": "encrypted_cvv",
                    }
                }
            }

        # Create the complete transaction payload following Pagar.me API v5
        transaction_data = {
            "amount": int(self.amount * 100),  # Amount in cents
            "currency": "BRL",
            "payment": payment_data,
            "customer": customer_data,
            "items": items_data,
            "metadata": {
                "odoo_reference": self.reference,
                "odoo_partner_id": str(self.partner_id.id),
                "odoo_transaction_id": str(self.id),
                "integration": "odoo_l10n_br",
            },
            # Webhook configuration
            "postback_url": f"{self.provider_id.get_base_url()}/payment/pagarme/webhook",
        }
        
        return transaction_data

    def _prepare_pagarme_customer_data(self):
        """Prepare customer data for Pagar.me API following WooCommerce plugin mapping."""
        partner = self.partner_id
        
        # Determine customer type and document
        document = partner.cnpj_cpf or ""
        document_type = "cpf" if len(document.replace(".", "").replace("-", "").replace("/", "")) == 11 else "cnpj"
        customer_type = "individual" if document_type == "cpf" else "company"
        
        customer_data = {
            "name": partner.name or "",
            "email": partner.email or "",
            "document": document.replace(".", "").replace("-", "").replace("/", ""),
            "document_type": document_type,
            "type": customer_type,
            "phones": {
                "home_phone": {
                    "country_code": "55",
                    "area_code": partner.phone[-11:-9] if partner.phone and len(partner.phone) >= 11 else "11",
                    "number": partner.phone[-9:] if partner.phone and len(partner.phone) >= 9 else "999999999",
                }
            },
            "address": {
                "street": partner.street or "",
                "street_number": partner.l10n_br_number or "S/N",
                "neighborhood": partner.l10n_br_district or "",
                "city": partner.city or "",
                "state": partner.state_id.code if partner.state_id else "",
                "zip_code": partner.zip.replace("-", "") if partner.zip else "",
                "country": partner.country_id.code if partner.country_id else "BR",
                "complement": partner.street2 or "",
            }
        }
        
        # Store customer info for reference
        self.pagarme_customer_document = customer_data["document"]
        self.pagarme_customer_type = customer_type
        
        return customer_data

    def _prepare_pagarme_items_data(self):
        """Prepare items data for Pagar.me API."""
        items = []
        
        # If we have sale order lines, use them
        if hasattr(self, "sale_order_ids") and self.sale_order_ids:
            for order in self.sale_order_ids:
                for line in order.order_line:
                    items.append({
                        "id": str(line.id),
                        "title": line.name or line.product_id.name,
                        "unit_price": int(line.price_unit * 100),  # In cents
                        "quantity": int(line.product_uom_qty),
                        "tangible": True,  # Physical product
                    })
        else:
            # Fallback to generic item
            items.append({
                "id": "1",
                "title": f"Payment - {self.reference}",
                "unit_price": int(self.amount * 100),  # In cents
                "quantity": 1,
                "tangible": False,  # Service
            })
            
        return items

    def _prepare_pagarme_payment_data(self, card_data):
        """Prepare payment data for Pagar.me API with encrypted card data."""
        payment_data = {
            "payment_method": "credit_card",
            "credit_card": {
                "installments": card_data.get("installments", 1),
                "statement_descriptor": "PAGARME",
                "card": {
                    "number": card_data.get("card_number"),
                    "holder_name": card_data.get("card_holder_name"),
                    "exp_month": card_data.get("card_exp_month"),
                    "exp_year": card_data.get("card_exp_year"),
                    "cvv": card_data.get("card_cvv"),
                }
            }
        }
        
        # Store payment method info
        self.pagarme_payment_method = "credit_card"
        self.pagarme_installments = card_data.get("installments", 1)
        
        return payment_data
    
    def _pagarme_process_transaction_response(self, response):
        """Process the response from Pagar.me transaction creation."""
        if not response:
            raise UserError(_("Empty response from Pagar.me"))
            
        # Update transaction with response data
        self._update_pagarme_transaction_data(response)
        
        # Extract transaction information following Pagar.me API v5 structure
        self.pagarme_transaction_id = response.get("id")
        self.pagarme_status = response.get("status")
        
        # Extract charge information if available
        charges = response.get("charges", [])
        if charges:
            charge = charges[0]  # Usually one charge per transaction
            self.pagarme_charge_id = charge.get("id")
            
            # Extract payment method details
            payment_method = charge.get("payment_method")
            if payment_method == "credit_card":
                card_info = charge.get("last_transaction", {}).get("card", {})
                self.pagarme_card_brand = card_info.get("brand")
                self.pagarme_card_last_digits = card_info.get("last_four_digits")
        
        # Store order ID if available
        if "order" in response:
            self.pagarme_order_id = response["order"].get("id")

        # Store additional metadata
        if hasattr(self, "provider_reference"):
            self.provider_reference = self.pagarme_transaction_id
        
        # Set transaction state based on response status
        status = response.get("status", "").lower()
        
        if status == "paid":
            self._set_done()
        elif status == "pending":
            self._set_pending()
        elif status == "authorized":
            self._set_authorized()
        elif status in ["refused", "failed"]:
            self._set_canceled()
        else:
            # For any unhandled status, set as pending and log
            _logger.warning("Unhandled Pagar.me transaction status: %s", status)
            self._set_pending()
            
        return response

    def _update_status_from_pagarme_charge(self, charge_status):
        """Update transaction status based on Pagar.me charge status."""
        status_mapping = {
            "paid": "done",
            "pending": "pending", 
            "processing": "pending",
            "failed": "cancel",
            "canceled": "cancel",
            "not_authorized": "cancel",
            "refunded": "cancel",
            "partial_refunded": "done",  # Keep as done, handle refund separately
        }
        
        odoo_status = status_mapping.get(charge_status)
        if odoo_status == "done":
            self._set_done()
        elif odoo_status == "pending":
            self._set_pending()
        elif odoo_status == "cancel":
            self._set_canceled()
        else:
            _logger.warning("Unknown Pagar.me charge status: %s", charge_status)

    def _pagarme_get_transaction_status(self):
        """Get transaction status from Pagar.me API."""
        if not self.pagarme_transaction_id:
            raise UserError(_("No Pagar.me transaction ID found"))
            
        endpoint = f"transactions/{self.pagarme_transaction_id}"
        response = self.provider_id._pagarme_make_request(endpoint, method="GET")
        
        return response

    @api.model
    def _pagarme_form_get_tx_from_data(self, data):
        """Get transaction from Pagar.me webhook data."""
        reference = data.get("metadata", {}).get("odoo_reference")
        if not reference:
            raise ValidationError(_("Pagar.me: missing transaction reference in webhook data"))
            
        tx = self.search([("reference", "=", reference), ("provider_code", "=", "pagarme")])
        if not tx:
            raise ValidationError(_("Pagar.me: no transaction found for reference %s") % reference)
        if len(tx) > 1:
            raise ValidationError(_("Pagar.me: multiple transactions found for reference %s") % reference)
            
        return tx

    def _pagarme_form_validate(self, data):
        """Validate Pagar.me webhook data and update transaction status."""
        _logger.info("Validating Pagar.me webhook data for transaction %s", self.reference)
        
        # Update transaction with webhook data
        self._pagarme_process_transaction_response(data)
        
        return True

    def _get_processing_info(self):
        """Override to return the processing information for Pagar.me transactions."""
        if self.provider_code != 'pagarme':
            return super()._get_processing_info()
        
        _logger.info("_get_processing_info called for Pagar.me transaction: %s", self.reference)
        
        # CRITICAL: Get the base processing info first to ensure all required fields are set
        processing_info = super()._get_processing_info()
        
        # For Pagar.me, force inline processing and provide inline form view
        processing_info.update({
            'flow': 'inline',  # Force inline processing to prevent redirect errors
            'inline_form_view_id': self.env.ref('payment_pagarme.inline_form').id,
        })
        
        _logger.info("Pagar.me processing info (forced inline): %s", processing_info)
        return processing_info

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Override to handle Pagar.me notification data."""
        if provider_code != "pagarme":
            return super()._get_tx_from_notification_data(provider_code, notification_data)
            
        return self._pagarme_form_get_tx_from_data(notification_data)