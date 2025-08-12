import requests

class PagarmeAPI:
    BASE_URL = 'https://api.pagar.me/core/v5'

    def __init__(self, api_key):
        self.api_key = api_key

    def tokenize_card(self, card_data):
        url = f'{self.BASE_URL}/cards'
        headers = {'Authorization': f'Bearer {self.api_key}'}
        data = {
            'number': card_data['number'],
            'holder_name': card_data['holder_name'],
            'expiration_date': card_data['expiration_date'],
            'cvv': card_data['cvv'],
        }
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()['id']
