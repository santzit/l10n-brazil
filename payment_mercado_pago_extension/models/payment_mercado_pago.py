from odoo import models, fields

class PaymentAcquirerMercadoPago(models.Model):
    _inherit = 'payment.acquirer'


    def _mercado_pago_prepare_payment_values(self, partner):
        """Extend payment values to include VAT/CPF and Name."""
        values = super()._mercado_pago_prepare_payment_values(partner)
        identification_type = None
        identification_number = None

        # Assuming partner.vat contains CPF or CNPJ
        if partner.vat:
            if len(partner.vat) == 11:
                identification_type = 'CPF'
            else:
                identification_type = 'CNPJ'
            identification_number = partner.vat

        values['payer'] = {
            'name': partner.name,
        }
        if identification_type and identification_number:
            values['payer']['identification'] = {
                'type': identification_type,
                'number': identification_number,
            }
        return values
