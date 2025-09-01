# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Provider: Pagar.me',
    'version': '16.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "Payment provider for Pagar.me integration in Brazilian localization.",
    'author': 'Odoo Community Association (OCA)',
    'depends': ['payment', 'l10n_br_base'],
    'data': [
        'views/payment_pagarme_templates.xml',
        'views/payment_provider_views.xml',
        'views/payment_token_views.xml',
        'views/payment_transaction_views.xml',

        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',  # Depends on `payment_method_pagarme`.
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'l10n_br_payment_pagarme/static/src/js/**/*',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}