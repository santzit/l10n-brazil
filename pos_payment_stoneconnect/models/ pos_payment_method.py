from odoo import models, fields

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    stone_terminal_id = fields.Char("Stone Terminal ID")
    stone_api_token = fields.Char("Stone API Token")
