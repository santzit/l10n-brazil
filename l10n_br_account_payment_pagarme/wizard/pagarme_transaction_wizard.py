# Copyright 2024 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PagarmeTransactionWizard(models.TransientModel):
    """Wizard for Pagar.me transaction operations."""
    
    _name = "pagarme.transaction.wizard"
    _description = "Pagar.me Transaction Wizard"

    operation = fields.Selection([
        ("capture", "Capture Transaction"),
        ("cancel", "Cancel Transaction"),
        ("refund", "Refund Transaction"),
    ], 
        string="Operation",
        required=True
    )

    transaction_id = fields.Many2one(
        "payment.transaction",
        string="Transaction",
        required=True,
        domain=[("provider_code", "=", "pagarme")]
    )

    amount = fields.Float(
        string="Amount",
        help="Amount to refund (leave empty for full refund)"
    )

    reason = fields.Text(
        string="Reason",
        help="Reason for the operation"
    )

    def action_execute_operation(self):
        """Execute the selected operation."""
        self.ensure_one()
        
        if self.operation == "capture":
            return self._capture_transaction()
        elif self.operation == "cancel":
            return self._cancel_transaction()
        elif self.operation == "refund":
            return self._refund_transaction()

    def _capture_transaction(self):
        """Capture an authorized transaction."""
        if self.transaction_id.state != "authorized":
            raise UserError(_("Transaction must be authorized to capture"))

        try:
            # Prepare capture data
            capture_data = {}
            if self.amount and self.amount != self.transaction_id.amount:
                capture_data["amount"] = int(self.amount * 100)

            # Make API call to capture
            provider = self.transaction_id.provider_id
            endpoint = f"transactions/{self.transaction_id.pagarme_transaction_id}/capture"
            response = provider._pagarme_make_request(endpoint, capture_data, "POST")

            # Update transaction
            self.transaction_id._pagarme_process_transaction_response(response)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Transaction Captured"),
                    'message': _("Transaction captured successfully"),
                    'type': 'success',
                }
            }

        except Exception as e:
            raise UserError(_("Error capturing transaction: %s") % str(e))

    def _cancel_transaction(self):
        """Cancel a transaction."""
        if self.transaction_id.state not in ("pending", "authorized"):
            raise UserError(_("Transaction cannot be canceled in current state"))

        try:
            # Make API call to cancel
            provider = self.transaction_id.provider_id
            endpoint = f"transactions/{self.transaction_id.pagarme_transaction_id}/cancel"
            cancel_data = {"reason": self.reason or "Canceled by merchant"}
            response = provider._pagarme_make_request(endpoint, cancel_data, "POST")

            # Update transaction
            self.transaction_id._set_canceled()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Transaction Canceled"),
                    'message': _("Transaction canceled successfully"),
                    'type': 'success',
                }
            }

        except Exception as e:
            raise UserError(_("Error canceling transaction: %s") % str(e))

    def _refund_transaction(self):
        """Refund a transaction."""
        if self.transaction_id.state != "done":
            raise UserError(_("Transaction must be completed to refund"))

        try:
            # Prepare refund data
            refund_data = {}
            if self.amount:
                refund_data["amount"] = int(self.amount * 100)
            if self.reason:
                refund_data["reason"] = self.reason

            # Make API call to refund
            provider = self.transaction_id.provider_id
            endpoint = f"transactions/{self.transaction_id.pagarme_transaction_id}/refund"
            response = provider._pagarme_make_request(endpoint, refund_data, "POST")

            # Create refund transaction
            refund_tx = self.transaction_id.copy({
                'amount': -(self.amount or self.transaction_id.amount),
                'operation': 'refund',
                'source_transaction_id': self.transaction_id.id,
            })
            refund_tx._pagarme_process_transaction_response(response)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Transaction Refunded"),
                    'message': _("Refund processed successfully"),
                    'type': 'success',
                }
            }

        except Exception as e:
            raise UserError(_("Error refunding transaction: %s") % str(e))