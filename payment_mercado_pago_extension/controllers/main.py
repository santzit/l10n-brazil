from odoo import http
from odoo.http import request

class MercadoPagoTransparentController(http.Controller):
    @http.route('/payment/mercado_pago/transparent', type='json', auth='public', methods=['POST'], csrf=False)
    def process_payment(self, **post):
        tx_id = post.get('tx_id')
        if not tx_id:
            return {'error': 'No transaction ID'}
        tx = request.env['payment.transaction'].sudo().browse(int(tx_id))
        result = tx.mercado_pago_api_charge(post)
        return result
