# Copyright 2024 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
import pprint

from odoo import http, _
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class PagarmeController(http.Controller):

    @http.route(
        "/payment/pagarme/payment",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def pagarme_payment(self, **post):
        """Handle Pagar.me payment form submission."""
        _logger.info("Pagar.me: processing payment form submission")
        
        try:
            # Get transaction reference
            reference = post.get("reference")
            if not reference:
                _logger.error("Pagar.me: missing reference in payment form")
                return request.redirect("/payment/process")
                
            # Find the transaction
            tx_sudo = request.env["payment.transaction"].sudo().search([
                ("reference", "=", reference),
                ("provider_code", "=", "pagarme"),
            ])
            
            if not tx_sudo:
                _logger.error("Pagar.me: no transaction found for reference %s", reference)
                return request.redirect("/payment/process")
                
            # Extract payment data from form
            card_data = {
                "card_number": post.get("pagarme_card_number", "").replace(" ", ""),
                "card_holder_name": post.get("pagarme_card_holder_name"),
                "card_exp_month": post.get("pagarme_card_exp_month"),
                "card_exp_year": post.get("pagarme_card_exp_year"),
                "card_cvv": post.get("pagarme_card_cvv"),
                "installments": int(post.get("pagarme_installments", 1)),
            }
            
            # Extract customer data from form
            customer_data = {
                "customer_name": post.get("pagarme_customer_name"),
                "customer_email": post.get("pagarme_customer_email"),
                "customer_document": post.get("pagarme_customer_document"),
                "customer_phone": post.get("pagarme_customer_phone"),
            }
            
            # Extract billing data from form  
            billing_data = {
                "billing_street": post.get("pagarme_billing_street"),
                "billing_street_number": post.get("pagarme_billing_street_number"),
                "billing_neighborhood": post.get("pagarme_billing_neighborhood"),
                "billing_city": post.get("pagarme_billing_city"),
                "billing_state": post.get("pagarme_billing_state"),
                "billing_zipcode": post.get("pagarme_zipcode"),
            }
            
            # Validate required fields
            if not all([
                card_data["card_number"],
                card_data["card_holder_name"],
                card_data["card_exp_month"],
                card_data["card_exp_year"],
                card_data["card_cvv"],
            ]):
                _logger.error("Pagar.me: missing required card information")
                return request.redirect("/payment/process")
                
            # Process the payment
            all_data = {**card_data, **customer_data, **billing_data}
            transaction_data = tx_sudo._pagarme_create_transaction_request(all_data)
            
            # Make request to Pagar.me API
            response = tx_sudo.provider_id._pagarme_make_request("transactions", transaction_data)
            
            # Process the response
            tx_sudo._pagarme_process_transaction_response(response)
            
            # Redirect to payment status page
            return request.redirect("/payment/status")
            
        except Exception as e:
            _logger.error("Pagar.me: error processing payment: %s", e)
            return request.redirect("/payment/process")

    @http.route(
        "/payment/pagarme/return",
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
        save_session=False,
    )
    def pagarme_return_from_checkout(self, **post):
        """Handle return from Pagar.me checkout."""
        _logger.info("Pagar.me: handling return from checkout with data:\n%s", pprint.pformat(post))
        
        # Handle the return data and redirect appropriately
        reference = post.get("reference")
        if not reference:
            _logger.error("Pagar.me: missing reference in return data")
            return request.redirect("/payment/process")
            
        # Find the transaction
        tx_sudo = request.env["payment.transaction"].sudo().search([
            ("reference", "=", reference),
            ("provider_code", "=", "pagarme"),
        ])
        
        if not tx_sudo:
            _logger.error("Pagar.me: no transaction found for reference %s", reference)
            return request.redirect("/payment/process")
            
        # Process the return data
        try:
            tx_sudo._handle_notification_data("pagarme", post)
        except ValidationError as e:
            _logger.error("Pagar.me: validation error processing return data: %s", e)
            
        return request.redirect("/payment/status")

    @http.route(
        "/payment/pagarme/webhook", 
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def pagarme_webhook(self, **kwargs):
        """Handle Pagar.me webhook notifications.
        
        This endpoint receives webhooks from Pagar.me and updates the 
        payment.transaction state accordingly. Supports the following events:
        - transaction.paid
        - transaction.refused  
        - transaction.refunded
        - transaction.chargeback
        - transaction.pending_refund
        """
        data = json.loads(request.httprequest.data.decode())
        _logger.info("Pagar.me: webhook received with data:\n%s", pprint.pformat(data))
        
        try:
            # Validate webhook data structure
            if "object" not in data or "id" not in data:
                _logger.error("Pagar.me: invalid webhook data structure")
                return {"status": "error", "message": "Invalid data structure"}
                
            webhook_object = data.get("object")
            webhook_id = data.get("id")
            
            # Handle different webhook types
            if webhook_object == "transaction":
                return self._handle_transaction_webhook(data)
            elif webhook_object == "subscription":
                return self._handle_subscription_webhook(data)
            else:
                _logger.warning("Pagar.me: unhandled webhook object type: %s", webhook_object)
                return {"status": "ignored", "message": f"Unhandled object type: {webhook_object}"}
                
        except Exception as e:
            _logger.error("Pagar.me: error processing webhook: %s", e)
            return {"status": "error", "message": str(e)}

    def _handle_transaction_webhook(self, data):
        """Handle transaction-related webhooks."""
        try:
            # Extract transaction data
            transaction_data = data
            
            # Find the transaction based on metadata
            metadata = transaction_data.get("metadata", {})
            reference = metadata.get("odoo_reference")
            
            if not reference:
                _logger.error("Pagar.me: missing odoo_reference in webhook metadata")
                return {"status": "error", "message": "Missing reference"}
                
            # Find and update the transaction
            tx_sudo = request.env["payment.transaction"].sudo().search([
                ("reference", "=", reference),
                ("provider_code", "=", "pagarme"),
            ])
            
            if not tx_sudo:
                _logger.error("Pagar.me: no transaction found for reference %s", reference)
                return {"status": "error", "message": "Transaction not found"}
                
            # Process the webhook data
            tx_sudo._handle_notification_data("pagarme", transaction_data)
            
            return {"status": "success"}
            
        except Exception as e:
            _logger.error("Pagar.me: error processing transaction webhook: %s", e)
            return {"status": "error", "message": str(e)}

    def _handle_subscription_webhook(self, data):
        """Handle subscription-related webhooks (for future use)."""
        _logger.info("Pagar.me: subscription webhook received (not implemented)")
        return {"status": "ignored", "message": "Subscription webhooks not implemented"}

    @http.route(
        "/payment/pagarme/process_payment",
        type="json", 
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def pagarme_process_payment(self, **kwargs):
        """Process transparent payment with Pagar.me.
        
        This endpoint handles the transparent checkout flow where card data
        is encrypted on the frontend and sent to this endpoint for processing.
        """
        _logger.info("Pagar.me: processing transparent payment")
        
        try:
            # Get transaction reference
            reference = kwargs.get("reference")
            if not reference:
                return {"status": "error", "message": "Missing transaction reference"}
                
            # Find the transaction
            tx_sudo = request.env["payment.transaction"].sudo().search([
                ("reference", "=", reference),
                ("provider_code", "=", "pagarme"),
            ])
            
            if not tx_sudo:
                return {"status": "error", "message": "Transaction not found"}
                
            # Get card data from request (encrypted by frontend)
            card_data = {
                "card_number": kwargs.get("card_number"),  
                "card_holder_name": kwargs.get("card_holder_name"),  
                "card_exp_month": kwargs.get("card_exp_month"),  
                "card_exp_year": kwargs.get("card_exp_year"),  
                "card_cvv": kwargs.get("card_cvv"),  
                "installments": kwargs.get("installments", 1),
            }
            
            # Get customer data from request
            customer_data = {
                "customer_name": kwargs.get("customer_name"),
                "customer_email": kwargs.get("customer_email"),
                "customer_document": kwargs.get("customer_document"),
                "customer_phone": kwargs.get("customer_phone"),
            }
            
            # Get billing data from request  
            billing_data = {
                "billing_street": kwargs.get("billing_street"),
                "billing_street_number": kwargs.get("billing_street_number"),
                "billing_neighborhood": kwargs.get("billing_neighborhood"),
                "billing_city": kwargs.get("billing_city"),
                "billing_state": kwargs.get("billing_state"),
                "billing_zipcode": kwargs.get("billing_zipcode"),
            }
            
            # Validate required card data
            if not all([
                card_data["card_number"],
                card_data["card_holder_name"], 
                card_data["card_exp_month"],
                card_data["card_exp_year"],
                card_data["card_cvv"],
            ]):
                return {"status": "error", "message": "Missing card information"}
                
            # Prepare transaction data for Pagar.me API
            all_data = {**card_data, **customer_data, **billing_data}
            transaction_data = tx_sudo._pagarme_create_transaction_request(all_data)
            
            # Make request to Pagar.me API
            response = tx_sudo.provider_id._pagarme_make_request("transactions", transaction_data)
            
            # Process the response
            tx_sudo._pagarme_process_transaction_response(response)
            
            return {
                "status": "success",
                "transaction_id": tx_sudo.pagarme_transaction_id,
                "redirect_url": "/payment/status",
            }
            
        except Exception as e:
            _logger.error("Pagar.me: error processing payment: %s", e)
            return {"status": "error", "message": str(e)}

    @http.route(
        "/payment/pagarme/get_installments",
        type="json",
        auth="public", 
        methods=["POST"],
        csrf=False,
    )
    def pagarme_get_installments(self, **kwargs):
        """Get available installments for a given amount.
        
        This endpoint calculates and returns available installment options
        based on the transaction amount and provider configuration.
        """
        try:
            amount = kwargs.get("amount")
            if not amount:
                return {"status": "error", "message": "Missing amount"}
                
            # Convert amount to float
            amount = float(amount)
            
            # Get provider configuration for installments
            # This would typically come from provider settings
            max_installments = 12  # Default max installments
            min_installment_amount = 5.00  # Minimum installment amount in BRL
            
            installments = []
            for i in range(1, max_installments + 1):
                installment_amount = amount / i
                if installment_amount >= min_installment_amount:
                    installments.append({
                        "installments": i,
                        "installment_amount": round(installment_amount, 2),
                        "total_amount": round(amount, 2),
                        "interest_rate": 0,  # No interest for now
                        "label": f"{i}x de R$ {installment_amount:.2f}".replace(".", ",")
                    })
                    
            return {
                "status": "success",
                "installments": installments,
            }
            
        except Exception as e:
            _logger.error("Pagar.me: error getting installments: %s", e)
            return {"status": "error", "message": str(e)}

    @http.route(
        "/payment/pagarme/validate_document", 
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def pagarme_validate_document(self, **kwargs):
        """Validate CPF/CNPJ document for Brazilian customers."""
        try:
            document = kwargs.get("document", "").replace(".", "").replace("-", "").replace("/", "")
            
            if not document:
                return {"status": "error", "message": "Document is required"}
                
            # Basic document validation
            if len(document) == 11:
                # CPF validation
                if self._validate_cpf(document):
                    return {"status": "success", "document_type": "cpf", "customer_type": "individual"}
                else:
                    return {"status": "error", "message": "Invalid CPF"}
            elif len(document) == 14:
                # CNPJ validation  
                if self._validate_cnpj(document):
                    return {"status": "success", "document_type": "cnpj", "customer_type": "company"}
                else:
                    return {"status": "error", "message": "Invalid CNPJ"}
            else:
                return {"status": "error", "message": "Document must have 11 (CPF) or 14 (CNPJ) digits"}
                
        except Exception as e:
            _logger.error("Pagar.me: error validating document: %s", e)
            return {"status": "error", "message": str(e)}

    def _validate_cpf(self, cpf):
        """Validate CPF number."""
        # Remove any formatting
        cpf = "".join(filter(str.isdigit, cpf))
        
        # Check if has 11 digits
        if len(cpf) != 11:
            return False
            
        # Check for invalid sequences
        if cpf == cpf[0] * 11:
            return False
            
        # Calculate verification digits
        def calculate_digit(cpf_partial):
            weight = len(cpf_partial) + 1
            total = sum(int(digit) * weight for digit, weight in zip(cpf_partial, range(weight, 1, -1)))
            remainder = total % 11
            return 0 if remainder < 2 else 11 - remainder
            
        # Validate first digit
        if int(cpf[9]) != calculate_digit(cpf[:9]):
            return False
            
        # Validate second digit  
        if int(cpf[10]) != calculate_digit(cpf[:10]):
            return False
            
        return True

    def _validate_cnpj(self, cnpj):
        """Validate CNPJ number."""
        # Remove any formatting
        cnpj = "".join(filter(str.isdigit, cnpj))
        
        # Check if has 14 digits
        if len(cnpj) != 14:
            return False
            
        # Check for invalid sequences
        if cnpj == cnpj[0] * 14:
            return False
            
        # Calculate verification digits
        def calculate_digit(cnpj_partial, weights):
            total = sum(int(digit) * weight for digit, weight in zip(cnpj_partial, weights))
            remainder = total % 11
            return 0 if remainder < 2 else 11 - remainder
            
        # First digit weights
        weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        if int(cnpj[12]) != calculate_digit(cnpj[:12], weights1):
            return False
            
        # Second digit weights
        weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        if int(cnpj[13]) != calculate_digit(cnpj[:13], weights2):
            return False
            
        return True