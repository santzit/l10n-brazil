# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class PagarmeCommon(PaymentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.pagarme = cls._prepare_provider(
            "pagarme",
            update_values={
                "pagarme_app_id": "app_test_1234567890",
                "pagarme_api_key": "sk_test_abcdef1234567890abcdef1234567890",
                "payment_icon_ids": [(5, 0, 0)],
            },
        )

        cls.provider = cls.pagarme

        cls.notification_data = {
            "id": "or_test_1234567890",
            "status": "paid",
            "amount": cls.amount * 100,  # Amount in cents
            "currency": "BRL",
            "metadata": {
                "reference": cls.reference,
            },
            "charges": [
                {
                    "id": "ch_test_1234567890",
                    "status": "paid",
                    "amount": cls.amount * 100,
                }
            ],
        }

        cls.failed_notification_data = {
            "id": "or_test_failed_1234567890",
            "status": "failed",
            "amount": cls.amount * 100,
            "currency": "BRL",
            "metadata": {
                "reference": cls.reference,
            },
            "charges": [
                {
                    "id": "ch_test_failed_1234567890",
                    "status": "failed",
                    "amount": cls.amount * 100,
                }
            ],
        }
