# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Brazilian Payment Provider: Pagar.me",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-brazil",
    "development_status": "Alpha", 
    "category": "Accounting/Payment Acquirers",
    "depends": [
        "payment",
        "l10n_br_base",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/payment_acquirer_views.xml",
        "views/payment_pagarme_templates.xml",
        "data/payment_acquirer_data.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "l10n_br_payment_pagarme/static/src/js/pagarme_form.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "external_dependencies": {
        "python": [
            "requests",
        ]
    },
}