# Copyright 2024 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Payment Pagar.me",
    "summary": "Stone/Pagar.me transparent checkout payment provider for Brazilian market",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-brazil",
    "category": "Accounting/Payment Providers",
    "depends": [
        "payment",
    ],
    "data": [
        "views/payment_provider_views.xml",
        "views/payment_pagarme_templates.xml",
        "data/pagarme_provider.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            # Pagar.me official JavaScript SDK for secure card tokenization
            ("include", "web._assets_helpers"),
            "https://assets.pagar.me/pagarme-js/4.11.0/pagarme.min.js",
            "payment_pagarme/static/src/js/payment_form.js",
        ],
    },
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
    "external_dependencies": {
        "python": [
            "requests",
        ]
    },
}