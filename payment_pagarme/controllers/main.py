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
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def pagarme_payment_json(self, **post):
        """Handle Pagar.me payment processing via JSON/AJAX."""
        _logger.info("Pagar.me: processing payment JSON request")
        _logger.info("Pagar.me: received POST data: %s", {k: ('***' if 'card' in k.lower() or 'cvv' in k.lower() else v) for k, v in post.items()})
        
        try:
            # Get required parameters
            provider_id = post.get("provider_id")
            reference = post.get("reference")
            payment_data = post.get("payment_data", {})
            access_token = post.get("access_token")
            
            _logger.info("Pagar.me: extracted parameters - provider_id: %s, reference: %s, has_payment_data: %s, has_access_token: %s", 
                        provider_id, reference, bool(payment_data), bool(access_token))
            
            if not all([provider_id, reference, payment_data, access_token]):
                missing = []
                if not provider_id: missing.append("provider_id")
                if not reference: missing.append("reference") 
                if not payment_data: missing.append("payment_data")
                if not access_token: missing.append("access_token")
                _logger.error("Pagar.me: missing required parameters: %s", missing)
                return {"status": "error", "message": f"Missing required parameters: {', '.join(missing)}"}
                
            # Find the transaction
            _logger.info("Pagar.me: searching for transaction with reference: %s, provider_id: %s", reference, provider_id)
            tx_sudo = request.env["payment.transaction"].sudo().search([
                ("reference", "=", reference),
                ("provider_code", "=", "pagarme"),
                ("provider_id", "=", provider_id),
            ])
            
            if not tx_sudo:
                _logger.error("Pagar.me: transaction not found for reference: %s, provider_id: %s", reference, provider_id)
                return {"status": "error", "message": "Transaction not found"}
            
            _logger.info("Pagar.me: found transaction: %s (ID: %s, state: %s)", tx_sudo.reference, tx_sudo.id, tx_sudo.state)
                
            # Validate access token
            _logger.info("Pagar.me: validating access token...")
            try:
                token_valid = tx_sudo._validate_notification_data("pagarme", {"access_token": access_token})
                if not token_valid:
                    _logger.error("Pagar.me: invalid access token for transaction %s", reference)
                    return {"status": "error", "message": "Invalid access token"}
                _logger.info("Pagar.me: access token validated successfully")
            except Exception as e:
                _logger.error("Pagar.me: error validating access token: %s", e)
                return {"status": "error", "message": "Access token validation failed"}
                
            # Validate required payment data
            required_fields = ["card_number", "card_holder_name", "card_exp_month", "card_exp_year", "card_cvv"]
            missing_fields = [field for field in required_fields if not payment_data.get(field)]
            if missing_fields:
                _logger.error("Pagar.me: missing required payment fields: %s", missing_fields)
                return {"status": "error", "message": f"Missing required payment information: {', '.join(missing_fields)}"}
            
            _logger.info("Pagar.me: payment data validation successful")
            _logger.info("Pagar.me: payment data overview - card_number: ****%s, installments: %s", 
                        payment_data.get("card_number", "")[-4:] if payment_data.get("card_number") else "missing",
                        payment_data.get("installments", "1"))
                
            # Process the payment
            _logger.info("Pagar.me: creating transaction request...")
            try:
                transaction_data = tx_sudo._pagarme_create_transaction_request(payment_data)
                _logger.info("Pagar.me: transaction request created successfully")
                _logger.debug("Pagar.me: transaction request data: %s", {k: ('***' if 'card' in k.lower() else v) for k, v in transaction_data.items()})
            except Exception as e:
                _logger.error("Pagar.me: error creating transaction request: %s", e)
                return {"status": "error", "message": "Failed to create transaction request"}
            
            _logger.info("Pagar.me: sending request to Pagar.me API...")
            try:
                response = tx_sudo.provider_id._pagarme_make_request("transactions", transaction_data)
                _logger.info("Pagar.me: API request completed")
                _logger.debug("Pagar.me: API response: %s", response)
            except Exception as e:
                _logger.error("Pagar.me: error making API request: %s", e)
                return {"status": "error", "message": "Payment gateway communication failed"}
            
            # Process the response
            _logger.info("Pagar.me: processing transaction response...")
            try:
                tx_sudo._pagarme_process_transaction_response(response)
                _logger.info("Pagar.me: transaction response processed successfully")
                _logger.info("Pagar.me: final transaction state: %s", tx_sudo.state)
            except Exception as e:
                _logger.error("Pagar.me: error processing transaction response: %s", e)
                return {"status": "error", "message": "Failed to process payment response"}
            
            _logger.info("Pagar.me: payment processing completed successfully for transaction %s", reference)
            return {"status": "success", "message": "Payment processed successfully"}
            
        except ValidationError as e:
            _logger.error("Pagar.me validation error: %s", e)
            return {"status": "error", "message": str(e)}
        except Exception as e:
            _logger.error("Pagar.me: unexpected error processing payment: %s", e, exc_info=True)
            return {"status": "error", "message": "Payment processing failed"}

    @http.route(
        "/payment/pagarme/get_installments",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def pagarme_get_installments(self, **post):
        """Get available installment options for the given amount."""
        try:
            amount = float(post.get("amount", 0))
            if amount <= 0:
                return {"status": "error", "message": "Invalid amount"}
            
            # Get Pagar.me provider
            provider = request.env["payment.provider"].sudo().search([
                ("code", "=", "pagarme"),
                ("state", "in", ["enabled", "test"]),
            ], limit=1)
            
            if not provider:
                return {"status": "error", "message": "Pagar.me provider not found"}
            
            # Calculate installments
            installments = []
            max_installments = min(provider.pagarme_max_installments, 12)
            min_amount = provider.pagarme_min_installment_amount
            
            for i in range(1, max_installments + 1):
                installment_amount = amount / i
                
                # Skip if installment amount is below minimum
                if installment_amount < min_amount:
                    continue
                    
                # No interest for first installment
                if i == 1:
                    label = f"1x de R$ {installment_amount:.2f} sem juros"
                    total_amount = amount
                else:
                    # Simple interest calculation (can be improved based on business rules)
                    interest_rate = 0.025  # 2.5% per month
                    total_with_interest = amount * (1 + (interest_rate * (i - 1)))
                    installment_with_interest = total_with_interest / i
                    
                    label = f"{i}x de R$ {installment_with_interest:.2f}"
                    total_amount = total_with_interest
                
                installments.append({
                    "installments": i,
                    "label": label,
                    "installment_amount": installment_amount,
                    "total_amount": total_amount,
                })
            
            return {
                "status": "success",
                "installments": installments
            }
            
        except Exception as e:
            _logger.error("Error calculating installments: %s", e)
            return {"status": "error", "message": "Error calculating installments"}

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
        _logger.info("Pagar.me: received form data: %s", {k: ('***' if 'card' in k.lower() or 'cvv' in k.lower() else v) for k, v in post.items()})
        
        try:
            # Get transaction reference
            reference = post.get("reference")
            if not reference:
                _logger.error("Pagar.me: missing reference in payment form")
                return request.redirect("/payment/process?error=missing_reference")
                
            _logger.info("Pagar.me: processing payment for reference: %s", reference)
                
            # Find the transaction
            tx_sudo = request.env["payment.transaction"].sudo().search([
                ("reference", "=", reference),
                ("provider_code", "=", "pagarme"),
            ])
            
            if not tx_sudo:
                _logger.error("Pagar.me: no transaction found for reference %s", reference)
                return request.redirect("/payment/process?error=transaction_not_found")
                
            _logger.info("Pagar.me: found transaction %s (ID: %s, state: %s)", tx_sudo.reference, tx_sudo.id, tx_sudo.state)
                
            # Extract payment data from form
            card_data = {
                "card_number": post.get("pagarme_card_number", "").replace(" ", ""),
                "card_holder_name": post.get("pagarme_card_holder_name"),
                "card_exp_month": post.get("pagarme_card_exp_month"),
                "card_exp_year": post.get("pagarme_card_exp_year"),
                "card_cvv": post.get("pagarme_card_cvv"),
                "installments": int(post.get("pagarme_installments", 1)),
            }
            
            _logger.info("Pagar.me: extracted card data - card_number: ****%s, holder: %s, exp: %s/%s, installments: %s", 
                        card_data["card_number"][-4:] if card_data["card_number"] else "none",
                        card_data["card_holder_name"], 
                        card_data["card_exp_month"], 
                        card_data["card_exp_year"],
                        card_data["installments"])
                        
            # Validate required fields
            if not all([
                card_data["card_number"],
                card_data["card_holder_name"],
                card_data["card_exp_month"],
                card_data["card_exp_year"],
                card_data["card_cvv"],
            ]):
                missing_fields = []
                if not card_data["card_number"]: missing_fields.append("card_number")
                if not card_data["card_holder_name"]: missing_fields.append("card_holder_name")
                if not card_data["card_exp_month"]: missing_fields.append("card_exp_month")
                if not card_data["card_exp_year"]: missing_fields.append("card_exp_year")
                if not card_data["card_cvv"]: missing_fields.append("card_cvv")
                
                _logger.error("Pagar.me: missing required card information: %s", missing_fields)
                return request.redirect(f"/payment/process?error=missing_card_data&fields={','.join(missing_fields)}")
                
            _logger.info("Pagar.me: card data validation successful")
                
            # Extract customer data from form (using transaction partner data as fallback)
            customer_data = {
                "customer_name": post.get("pagarme_customer_name") or tx_sudo.partner_id.name,
                "customer_email": post.get("pagarme_customer_email") or tx_sudo.partner_id.email,
                "customer_document": post.get("pagarme_customer_document") or tx_sudo.partner_id.cnpj_cpf,
                "customer_phone": post.get("pagarme_customer_phone") or tx_sudo.partner_id.phone or tx_sudo.partner_id.mobile,
            }
            
            # Extract billing data from form (using transaction partner data as fallback)
            billing_data = {
                "billing_street": post.get("pagarme_billing_street") or tx_sudo.partner_id.street,
                "billing_street_number": post.get("pagarme_billing_street_number") or tx_sudo.partner_id.l10n_br_number,
                "billing_neighborhood": post.get("pagarme_billing_neighborhood") or tx_sudo.partner_id.l10n_br_district,
                "billing_city": post.get("pagarme_billing_city") or tx_sudo.partner_id.city,
                "billing_state": post.get("pagarme_billing_state") or (tx_sudo.partner_id.state_id.code if tx_sudo.partner_id.state_id else ""),
                "billing_zipcode": post.get("pagarme_zipcode") or tx_sudo.partner_id.zip,
            }
            
            _logger.info("Pagar.me: creating transaction request...")
            
            # Process the payment
            all_data = {**card_data, **customer_data, **billing_data}
            transaction_data = tx_sudo._pagarme_create_transaction_request(all_data)
            
            _logger.info("Pagar.me: sending request to Pagar.me API...")
            
            # Make request to Pagar.me API
            response = tx_sudo.provider_id._pagarme_make_request("transactions", transaction_data)
            
            _logger.info("Pagar.me: processing response...")
            
            # Process the response
            tx_sudo._pagarme_process_transaction_response(response)
            
            _logger.info("Pagar.me: payment processed successfully, redirecting to status page")
            
            # Redirect to payment status page
            return request.redirect("/payment/status")
            
        except Exception as e:
            _logger.error("Pagar.me: error processing payment: %s", e, exc_info=True)
            return request.redirect("/payment/process?error=payment_failed")

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