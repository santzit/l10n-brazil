# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon


@tagged('post_install', '-at_install')
class TestPaymentProviderPagarme(PaymentCommon):

    def setUp(self):
        super().setUp()
        self.pagarme = self._prepare_provider('pagarme', update_values={
            'state': 'test',
        })

    def test_provider_pagarme_creation(self):
        """Test that the Pagar.me provider can be created."""
        self.assertEqual(self.pagarme.code, 'pagarme')
        self.assertEqual(self.pagarme.state, 'test')

    def test_processing_values_include_pagarme_data(self):
        """Test that the processing values are correctly handled."""
        tx = self._create_transaction(flow='direct', provider=self.pagarme)
        processing_values = tx._get_processing_values()
        self.assertIn('provider_code', processing_values)
        self.assertEqual(processing_values['provider_code'], 'pagarme')