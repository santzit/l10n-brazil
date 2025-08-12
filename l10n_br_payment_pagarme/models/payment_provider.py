from odoo import fields, models

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('pagarme', "Pagar.me")],
        ondelete={'pagarme': 'set default'},
        default='manual'  # 👈 This avoids the error
    )

    pagarme_public_key = fields.Char(string="Pagar.me Public Key")
    pagarme_api_key = fields.Char("Pagar.me Secret API Key", groups='base.group_system')
    pagarme_secret_key = fields.Char("Pagar.me Secret API Key", groups='base.group_system')
    pagarme_encryption_key = fields.Char("Encryption Key", groups='base.group_system')
    pagarme_use_sandbox = fields.Boolean("Use Sandbox")

    def _get_default_payment_method(self):
        self.ensure_one()
        return self.env.ref('payment.method_electronic')
