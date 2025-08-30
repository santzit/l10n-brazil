# Copyright 2024 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Brazilian Payment Provider - Pagar.me",
    "summary": "Pagar.me payment gateway integration for Brazilian payments",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-brazil",
    "development_status": "Beta",
    "category": "Banking addons",
    "depends": [
        "l10n_br_account_payment_order",
        "payment",  # Base payment provider functionality
    ],
    "data": [
        # Security
        "security/ir.model.access.csv",
        # Data
        "data/payment_provider.xml",
        "data/payment_method.xml",
        # Views
        "views/payment_provider_views.xml",
        "views/account_payment_order_views.xml",
        "views/l10n_br_cnab_config_views.xml",
        # Wizards
        "wizard/pagarme_transaction_wizard_views.xml",
    ],
    "demo": [
        "demo/payment_provider_demo.xml",
        "demo/account_payment_mode_demo.xml",
    ],
    "external_dependencies": {
        "python": [
            "requests",
            "cryptography",
        ]
    },
    "installable": True,
    "auto_install": False,
}