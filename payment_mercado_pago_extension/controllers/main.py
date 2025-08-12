from odoo import http
from odoo.http import request

class MercadoPagoTransparentController(http.Controller):
    
    @http.route('/payment/mercado_pago/transparent', type='json', auth='public', methods=['POST'], csrf=False)
    def process_payment(self, **post):
        """Original endpoint for transparent payments."""
        tx_id = post.get('tx_id')
        if not tx_id:
            return {'error': 'No transaction ID'}
        tx = request.env['payment.transaction'].sudo().browse(int(tx_id))
        result = tx.mercado_pago_api_charge(post)
        return result
    
    @http.route('/payment/mercado_pago/charge', type='json', auth='public', methods=['POST'], csrf=False)
    def charge_payment(self, **post):
        """Endpoint for Mercado Pago transparent payments, simulating payment success."""
        # Extract transaction ID from session or form data
        tx_id = post.get('tx_id') or request.session.get('tx_id')
        
        if not tx_id:
            return {'error': 'No transaction ID provided'}
        
        try:
            tx = request.env['payment.transaction'].sudo().browse(int(tx_id))
            if not tx.exists():
                return {'error': 'Transaction not found'}
            
            # Process the payment with Mercado Pago data
            result = tx.mercado_pago_api_charge(post)
            return result
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Payment processing failed: {str(e)}'
            }
