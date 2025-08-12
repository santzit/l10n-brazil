from odoo import models, fields

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    pagarme_api_key = fields.Char("Pagarme API Key")
