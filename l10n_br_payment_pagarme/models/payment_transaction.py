from odoo import models, fields, api
import requests

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    pagarme_charge_id = fields.Char("Pagar.me Charge ID")

    def _execute_pagarme_direct_payment(self):
        for tx in self:
            acquirer = tx.provider_id
            headers = {'Authorization': f'Bearer {acquirer.pagarme_api_key}'}
            url = 'https://api.pagar.me/core/v5/charges'

            payload = {
                "amount": int(tx.amount * 100),
                "payment_method": "credit_card",
                "credit_card": {
                    "card_hash": tx.acquirer_reference,  # This is the encrypted hash received from the frontend
                },
                "customer": {
                    "name": tx.partner_id.name,
                    "email": tx.partner_id.email,
                },
                "capture": True,
            }

            response = requests.post(url, json=payload, headers=headers)
            result = response.json()
            if response.status_code == 200 and result.get("status") == "paid":
                tx.write({
                    'state': 'done',
                    'acquirer_reference': result['id'],
                })
            else:
                tx.write({
                    'state': 'error',
                    'state_message': result.get('message', 'Pagar.me charge failed')
                })
