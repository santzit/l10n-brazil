# Copyright 2024 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Stone/Pagar.me Payment Provider",
    "summary": "Stone/Pagar.me transparent checkout payment provider for Brazilian market",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-brazil",
    "category": "Accounting/Payment Acquirers",
    "depends": [
        "payment",
        "l10n_br_base",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/payment_provider_data.xml",
        "views/payment_provider_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "stone_pagarme_payment/static/src/css/stone_pagarme.css",
            "stone_pagarme_payment/static/src/js/stone_pagarme.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "external_dependencies": {
        "python": [
            "requests",
        ]
    },
}