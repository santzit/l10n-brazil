# Copyright 2024 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
import requests
from werkzeug.urls import url_encode

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("stone_pagarme", "Stone/Pagar.me")],
        ondelete={"stone_pagarme": "set default"}
    )
    
    # Stone/Pagar.me API Configuration
    stone_pagarme_api_key = fields.Char(
        string="API Key",
        help="Stone/Pagar.me API Key",
        required_if_provider="stone_pagarme",
        groups="base.group_system",
    )
    stone_pagarme_encryption_key = fields.Char(
        string="Encryption Key", 
        help="Stone/Pagar.me Encryption Key for card data",
        required_if_provider="stone_pagarme",
        groups="base.group_system",
    )
    stone_pagarme_webhook_url = fields.Char(
        string="Webhook URL",
        help="URL to receive payment notifications",
        compute="_compute_stone_pagarme_webhook_url",
        readonly=True,
    )

    @api.depends("code", "company_id")
    def _compute_stone_pagarme_webhook_url(self):
        """Compute the webhook URL for payment notifications."""
        for provider in self:
            if provider.code == "stone_pagarme":
                base_url = provider.get_base_url()
                provider.stone_pagarme_webhook_url = f"{base_url}/payment/stone_pagarme/webhook"
            else:
                provider.stone_pagarme_webhook_url = False

    def _get_supported_currencies(self):
        """Return the supported currencies."""
        supported_currencies = super()._get_supported_currencies()
        if self.code == "stone_pagarme":
            supported_currencies = supported_currencies.filtered(lambda c: c.name == "BRL")
        return supported_currencies

    def _stone_pagarme_get_api_url(self):
        """Return the API URL based on the provider state."""
        if self.state == "enabled":
            return "https://api.pagar.me/core/v5"
        else:
            return "https://api.pagar.me/core/v5"  # Same for test in this case

    def _stone_pagarme_make_request(self, endpoint, data=None, method="POST"):
        """Make a request to Stone/Pagar.me API."""
        url = f"{self._stone_pagarme_get_api_url()}/{endpoint}"
        headers = {
            "Authorization": f"Basic {self.stone_pagarme_api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            if method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            _logger.error(
                "Stone/Pagar.me API request failed: %s. URL: %s, Data: %s",
                e, url, data
            )
            raise UserError(_("Payment processing failed. Please try again later."))

    def _stone_pagarme_get_supported_payment_methods(self):
        """Return the supported payment methods."""
        return ["card"]

    def _prepare_stone_pagarme_customer_data(self, partner):
        """Prepare customer data for Stone/Pagar.me API."""
        customer_data = {
            "name": partner.name,
            "email": partner.email or "",
            "type": "individual" if partner.is_company else "individual",
        }
        
        # Add document (CPF/CNPJ)
        if hasattr(partner, "cnpj_cpf") and partner.cnpj_cpf:
            # Remove formatting from CPF/CNPJ
            document = "".join(filter(str.isdigit, partner.cnpj_cpf))
            if len(document) == 11:  # CPF
                customer_data["document"] = document
                customer_data["document_type"] = "cpf"
            elif len(document) == 14:  # CNPJ
                customer_data["document"] = document
                customer_data["document_type"] = "cnpj"
                customer_data["type"] = "corporation"
        
        # Add phone
        if partner.phone:
            phone = "".join(filter(str.isdigit, partner.phone))
            if len(phone) >= 10:
                customer_data["phones"] = {
                    "home_phone": {
                        "country_code": "55",
                        "area_code": phone[:2] if len(phone) >= 10 else "11",
                        "number": phone[2:] if len(phone) >= 10 else phone,
                    }
                }
        
        # Add address
        if partner.street:
            address_data = {
                "line_1": partner.street,
                "line_2": partner.street2 or "",
                "zip_code": "".join(filter(str.isdigit, partner.zip or "")),
                "city": partner.city or "",
                "state": partner.state_id.code if partner.state_id else "",
                "country": partner.country_id.code if partner.country_id else "BR",
            }
            customer_data["address"] = address_data
            
        return customer_data

    def _prepare_stone_pagarme_order_data(self, tx_values):
        """Prepare order data for Stone/Pagar.me API."""
        currency = self.env["res.currency"].browse(tx_values["currency_id"])
        amount_cents = int(tx_values["amount"] * 100)  # Convert to cents
        
        order_data = {
            "amount": amount_cents,
            "currency": currency.name,
            "items": [],
        }
        
        # Add order items if available
        if "sale_order_ids" in tx_values and tx_values["sale_order_ids"]:
            sale_order = self.env["sale.order"].browse(tx_values["sale_order_ids"][0])
            for line in sale_order.order_line:
                order_data["items"].append({
                    "id": str(line.id),
                    "title": line.name,
                    "unit_price": int(line.price_unit * 100),
                    "quantity": int(line.product_uom_qty),
                    "tangible": True,
                })
        else:
            # Default item for the transaction
            order_data["items"].append({
                "id": "1",
                "title": tx_values.get("reference", "Payment"),
                "unit_price": amount_cents,
                "quantity": 1,
                "tangible": False,
            })
            
        return order_data

    def _prepare_stone_pagarme_payment_data(self, tx_values, payment_method_data):
        """Prepare complete payment data for Stone/Pagar.me API."""
        partner = self.env["res.partner"].browse(tx_values["partner_id"])
        
        payment_data = {
            "payment_method": "credit_card",
            "credit_card": payment_method_data,
        }
        
        return payment_data

    @api.model 
    def _get_compatible_providers(self, *args, currency_id=None, **kwargs):
        """Override to ensure Stone/Pagar.me only works with BRL."""
        providers = super()._get_compatible_providers(*args, currency_id=currency_id, **kwargs)
        
        if currency_id:
            currency = self.env["res.currency"].browse(currency_id)
            if currency.name != "BRL":
                providers = providers.filtered(lambda p: p.code != "stone_pagarme")
                
        return providers