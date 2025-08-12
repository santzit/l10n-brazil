{
    'name': 'Mercado Pago Transparent Checkout',
    'version': '16.0.1.0.0',
    'category': 'Accounting/Payment Acquirers',
    'summary': 'Integration with Mercado Pago Transparent Checkout for Odoo payments',
    'description': '''
        This module integrates Mercado Pago Transparent Checkout as a payment provider in Odoo.
        It allows customers to pay directly via Mercado Pago without redirection.
        
        Features:
        - Transparent checkout integration with Mercado Pago SDK
        - Support for CPF/CNPJ identification
        - Brazilian Portuguese interface
        - Ready for production with API integration stubs
    ''',
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'depends': [
        'payment',
        'l10n_br_base',  # For Brazilian localization features
    ],
    'data': [
        'views/payment_acquirer_views.xml',
        'templates/transparent_checkout.xml',
        'data/payment_acquirer_demo.xml',
    ],
    'demo': [
        'data/payment_acquirer_demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_mercado_pago_extension/static/src/js/mercado_pago_transparent.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}