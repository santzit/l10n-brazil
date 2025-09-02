# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class PagarmeCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.pagarme = cls._prepare_provider('pagarme', update_values={
            'pagarme_merchant_id': 'dummy',
            'pagarme_secret_key': 'dummy',
        })


class TestPaymentProvider(PagarmeCommon):

    def test_compatible_providers(self):
        providers = self.env['payment.provider']._get_compatible_providers(
            self.company.id, self.partner.id, self.amount
        )
        self.assertIn(self.pagarme, providers)