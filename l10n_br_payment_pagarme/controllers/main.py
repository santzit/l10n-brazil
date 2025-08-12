from odoo import http
from odoo.http import request
import requests

class PagarmeController(http.Controller):
    @http.route('/payment/pagarme/tokenize', type='json', auth='public')
    def tokenize(self, **kwargs):
        acquirer = request.env['payment.provider'].sudo().browse(int(kwargs['provider_id']))
        headers = {'Authorization': f'Bearer {acquirer.pagarme_api_key}'}
        url = 'https://api.pagar.me/core/v5/cards'
        payload = kwargs['card']
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return {'card_id': response.json()['id']}
