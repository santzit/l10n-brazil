{
    "name": "Pagar.me Payment Provider",
    "version": "16.0.1.0.0",
    "category": "Accounting/Payment Acquirers",
    "license": "AGPL-3",
    "author": "OCA",
    "website": "https://github.com/OCA/l10n-brazil",
    "depends": [
        "payment",
        "l10n_br_base",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/payment_acquirer_data.xml",
        "views/payment_pagarme_views.xml",
        "views/payment_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "payment_pagarme/static/src/js/payment_form.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "summary": "Payment Provider for Pagar.me with secure tokenization",
    "description": """
Pagar.me Payment Provider for Odoo 16
=====================================

This module provides integration with Pagar.me payment gateway for Brazilian e-commerce.

Features:
* Secure frontend card tokenization (card data never touches server)
* Credit card payments via Pagar.me REST API
* PCI compliance through tokenization
* Brazilian market optimization
* Webhook support for payment status updates

Security:
* All card data is tokenized in the browser before submission
* Only tokens are processed on the backend
* No sensitive payment data stored in Odoo
    """,
    "external_dependencies": {
        "python": ["requests"],
    },
}