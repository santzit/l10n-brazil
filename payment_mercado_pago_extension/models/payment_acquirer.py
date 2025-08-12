from odoo import models, fields

class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    mercado_pago_public_key = fields.Char(
        string='Mercado Pago Public Key',
        help='Public key provided by Mercado Pago for transparent checkout',
        groups='base.group_user'
    )

    def _mercado_pago_prepare_payment_values(self, partner):
        """Prepare payment values to include VAT/CPF and Name for Brazilian customers."""
        values = {}
        identification_type = None
        identification_number = None

        # Assuming partner.vat contains CPF or CNPJ
        if partner.vat:
            # Remove any formatting characters
            vat_clean = ''.join(filter(str.isdigit, partner.vat))
            if len(vat_clean) == 11:
                identification_type = 'CPF'
            elif len(vat_clean) == 14:
                identification_type = 'CNPJ'
            identification_number = vat_clean

        values['payer'] = {
            'name': partner.name,
        }
        if identification_type and identification_number:
            values['payer']['identification'] = {
                'type': identification_type,
                'number': identification_number,
            }
        return values
