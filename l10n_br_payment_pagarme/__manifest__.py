{
    "name": "Brazilian Pagar.me Payment Provider",
    "version": "16.0.1.0.0",
    "category": "Accounting/Payment Providers",
    "license": "AGPL-3",
    "author": "OCA",
    "website": "https://github.com/OCA/l10n-brazil",
    "depends": [
        "payment",
    ],
    "data": [
        "data/pagarme_provider.xml",
        "views/payment_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "l10n_br_payment_pagarme/static/src/js/payment_form.js",
        ],
    },
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "auto_install": False,
    "summary": "Brazilian Payment Provider for Pagar.me",
    "description": """
Brazilian Pagar.me Payment Provider for Odoo 16
===============================================

Payment integration with Pagar.me gateway for Brazilian e-commerce.
    """,
    "external_dependencies": {
        "python": ["requests"],
    },
}
