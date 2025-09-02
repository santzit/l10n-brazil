# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Provider: Pagar.me',
    'version': '2.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "A payment provider for Pagar.me with Brazilian localization support.",
    'description': " ",  # Non-empty string to avoid loading the README file.
    'depends': ['payment', 'l10n_br_base'],
    'data': [
        'views/payment_pagarme_templates.xml',
        'views/payment_templates.xml',
        'views/payment_token_views.xml',
        'views/payment_transaction_views.xml',
        'data/payment_provider_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'l10n_br_payment_pagarme/static/src/js/**/*',
        ],
    },
    'license': 'LGPL-3',
}