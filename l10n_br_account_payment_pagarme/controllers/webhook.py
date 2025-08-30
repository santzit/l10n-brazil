# Copyright 2024 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import hashlib
import hmac
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PagarmeWebhookController(http.Controller):
    """Controller for handling Pagar.me webhooks."""

    @http.route('/payment/pagarme/webhook', type='json', auth='public', 
                methods=['POST'], csrf=False, save_session=False)
    def pagarme_webhook(self, **kwargs):
        """Handle Pagar.me webhook notifications."""
        try:
            # Get webhook data
            webhook_data = request.jsonrequest
            if not webhook_data:
                _logger.warning("Received empty webhook data from Pagar.me")
                return {'status': 'error', 'message': 'Empty webhook data'}

            # Validate webhook signature
            if not self._validate_webhook_signature(webhook_data):
                _logger.warning("Invalid webhook signature from Pagar.me")
                return {'status': 'error', 'message': 'Invalid signature'}

            # Process webhook event
            event_type = webhook_data.get('type')
            _logger.info("Processing Pagar.me webhook event: %s", event_type)

            if event_type in ['transaction.paid', 'transaction.authorized', 
                            'transaction.refused', 'transaction.refunded']:
                self._process_transaction_webhook(webhook_data)
            elif event_type in ['charge.paid', 'charge.failed', 'charge.canceled']:
                self._process_charge_webhook(webhook_data)
            elif event_type in ['order.paid', 'order.canceled']:
                self._process_order_webhook(webhook_data)
            else:
                _logger.info("Unhandled webhook event type: %s", event_type)

            return {'status': 'success'}

        except Exception as e:
            _logger.error("Error processing Pagar.me webhook: %s", str(e))
            return {'status': 'error', 'message': str(e)}

    @http.route('/payment/pagarme/webhook/<int:config_id>', type='json', 
                auth='public', methods=['POST'], csrf=False, save_session=False)
    def pagarme_webhook_config(self, config_id, **kwargs):
        """Handle Pagar.me webhook for specific CNAB config."""
        try:
            # Get CNAB config
            cnab_config = request.env['l10n_br_cnab_config'].sudo().browse(config_id)
            if not cnab_config.exists():
                return {'status': 'error', 'message': 'Invalid config ID'}

            webhook_data = request.jsonrequest
            if not webhook_data:
                return {'status': 'error', 'message': 'Empty webhook data'}

            # Validate webhook signature with config-specific secret
            if not self._validate_webhook_signature(webhook_data, cnab_config.pagarme_webhook_secret):
                return {'status': 'error', 'message': 'Invalid signature'}

            # Process webhook for payment order
            self._process_payment_order_webhook(webhook_data, cnab_config)

            return {'status': 'success'}

        except Exception as e:
            _logger.error("Error processing Pagar.me config webhook: %s", str(e))
            return {'status': 'error', 'message': str(e)}

    def _validate_webhook_signature(self, webhook_data, webhook_secret=None):
        """Validate webhook signature from Pagar.me."""
        try:
            # Get signature from headers
            signature = request.httprequest.headers.get('X-Hub-Signature')
            if not signature:
                # Some webhooks might use different header names
                signature = request.httprequest.headers.get('X-Pagarme-Signature')
            
            if not signature:
                _logger.warning("No webhook signature found in headers")
                return False

            # Get webhook secret from system parameters or config
            if not webhook_secret:
                webhook_secret = request.env['ir.config_parameter'].sudo().get_param(
                    'pagarme.webhook_secret', ''
                )

            if not webhook_secret:
                _logger.warning("No webhook secret configured")
                return True  # Skip validation if no secret is configured

            # Calculate expected signature
            payload = json.dumps(webhook_data, separators=(',', ':')).encode('utf-8')
            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()

            # Compare signatures
            expected_signature = f"sha256={expected_signature}"
            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            _logger.error("Error validating webhook signature: %s", str(e))
            return False

    def _process_transaction_webhook(self, webhook_data):
        """Process transaction-related webhook events."""
        transaction_data = webhook_data.get('data', {})
        transaction_id = transaction_data.get('id')

        if not transaction_id:
            _logger.warning("No transaction ID in webhook data")
            return

        # Find payment transaction by Pagar.me ID
        payment_transaction = request.env['payment.transaction'].sudo().search([
            ('pagarme_transaction_id', '=', transaction_id)
        ], limit=1)

        if payment_transaction:
            payment_transaction._pagarme_webhook_process(webhook_data)
        else:
            _logger.warning("Payment transaction not found for Pagar.me ID: %s", transaction_id)

    def _process_charge_webhook(self, webhook_data):
        """Process charge-related webhook events."""
        charge_data = webhook_data.get('data', {})
        charge_id = charge_data.get('id')

        if not charge_id:
            return

        # Find payment transaction by charge ID
        payment_transaction = request.env['payment.transaction'].sudo().search([
            ('pagarme_charge_id', '=', charge_id)
        ], limit=1)

        if payment_transaction:
            payment_transaction._pagarme_webhook_process(webhook_data)

    def _process_order_webhook(self, webhook_data):
        """Process order-related webhook events."""
        order_data = webhook_data.get('data', {})
        
        # Extract transaction IDs from order charges
        charges = order_data.get('charges', [])
        for charge in charges:
            transactions = charge.get('transactions', [])
            for transaction in transactions:
                transaction_id = transaction.get('id')
                if transaction_id:
                    payment_transaction = request.env['payment.transaction'].sudo().search([
                        ('pagarme_transaction_id', '=', transaction_id)
                    ], limit=1)
                    
                    if payment_transaction:
                        # Create modified webhook data for transaction
                        transaction_webhook = {
                            'type': webhook_data.get('type'),
                            'data': transaction,
                            'created_at': webhook_data.get('created_at'),
                        }
                        payment_transaction._pagarme_webhook_process(transaction_webhook)

    def _process_payment_order_webhook(self, webhook_data, cnab_config):
        """Process webhook for payment order context."""
        # Find payment orders using this CNAB config
        payment_orders = request.env['account.payment.order'].sudo().search([
            ('payment_mode_id.cnab_config_id', '=', cnab_config.id),
            ('state', 'in', ['uploaded', 'done'])
        ])

        for order in payment_orders:
            try:
                order._pagarme_webhook_update_order(webhook_data)
            except Exception as e:
                _logger.error("Error updating payment order %s: %s", order.name, str(e))

    @http.route('/payment/pagarme/return', type='http', auth='public', 
                methods=['GET', 'POST'], csrf=False, save_session=False)
    def pagarme_return(self, **kwargs):
        """Handle return from Pagar.me payment page."""
        try:
            # Get transaction reference from parameters
            tx_ref = kwargs.get('reference') or kwargs.get('tx_ref')
            if not tx_ref:
                return request.redirect('/payment/process')

            # Find transaction
            tx = request.env['payment.transaction'].sudo().search([
                ('reference', '=', tx_ref),
                ('provider_code', '=', 'pagarme')
            ], limit=1)

            if not tx:
                return request.redirect('/payment/process?error=transaction_not_found')

            # Check transaction status
            if kwargs.get('status') == 'success':
                tx._set_done()
            elif kwargs.get('status') == 'failed':
                tx._set_error(kwargs.get('error_message', 'Payment failed'))

            return request.redirect('/payment/process?tx_id=%s' % tx.id)

        except Exception as e:
            _logger.error("Error processing Pagar.me return: %s", str(e))
            return request.redirect('/payment/process?error=processing_error')