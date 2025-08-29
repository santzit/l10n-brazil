{
    "name": "Pagar.me Payment Provider",
    "version": "16.0.1.0.0",
    "category": "Accounting/Payment Acquirers",
    "license": "AGPL-3",
    "author": "OCA",
    "website": "https://github.com/OCA/l10n-brazil",
    "depends": [
        "payment",
    ],
    "data": [
        "views/payment_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "summary": "Payment Provider for Pagar.me",
    "description": """
Pagar.me Payment Provider for Odoo 16
=====================================

Simple integration with Pagar.me payment gateway for Brazilian e-commerce.
    """,
    "external_dependencies": {
        "python": ["requests"],
    },
}