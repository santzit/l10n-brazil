# Copyright 2024 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMove(models.Model):
    """Account Move integration with Pagar.me."""
    
    _inherit = "account.move"

    # Pagar.me payment tracking
    pagarme_transaction_ids = fields.One2many(
        "payment.transaction",
        "source_transaction_id",
        string="Pagar.me Transactions",
        domain=[("provider_code", "=", "pagarme")],
        help="Pagar.me transactions associated with this invoice"
    )

    pagarme_payment_status = fields.Selection([
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ],
        string="Pagar.me Payment Status",
        compute="_compute_pagarme_payment_status",
        store=True,
        help="Overall payment status from Pagar.me"
    )

    def _compute_pagarme_payment_status(self):
        """Compute Pagar.me payment status based on transactions."""
        for move in self:
            transactions = move.pagarme_transaction_ids
            if not transactions:
                move.pagarme_payment_status = False
            elif all(t.state == "done" for t in transactions):
                move.pagarme_payment_status = "paid"
            elif any(t.state == "error" for t in transactions):
                move.pagarme_payment_status = "failed"
            elif any(t.state == "cancel" for t in transactions):
                move.pagarme_payment_status = "refunded"
            elif any(t.state in ("pending", "authorized") for t in transactions):
                move.pagarme_payment_status = "processing"
            else:
                move.pagarme_payment_status = "pending"

    def action_view_pagarme_transactions(self):
        """Action to view Pagar.me transactions."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pagar.me Transactions',
            'res_model': 'payment.transaction',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.pagarme_transaction_ids.ids)],
            'context': {'default_source_transaction_id': self.id},
        }