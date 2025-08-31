# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.l10n_br_payment_pagarme.controllers.main import PagarmeController
from odoo.addons.l10n_br_payment_pagarme.tests.common import PaymentPagarmeCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon


@tagged("-at_install", "post_install")
class TestProcessingFlows(PaymentPagarmeCommon, PaymentHttpCommon):
    def test_portal_payment_triggers_processing(self):
        """Test that webhook from Pagar.me triggers the processing of the
        notification data."""
        tx = self._create_transaction(
            flow="direct", reference=f"{self.reference}-webhook"
        )
        # Set order ID for webhook lookup
        tx.provider_reference = "or_test_1234567890"

        url = self._build_url(PagarmeController._webhook_url)
        webhook_data = {
            "type": "order.paid",
            "data": {"id": "or_test_1234567890"},
        }

        with patch(
            "odoo.addons.payment.models.payment_transaction.PaymentTransaction"
            "._handle_notification_data"
        ) as handle_notification_data_mock:
            self._make_json_request(url, data=webhook_data)
        self.assertEqual(handle_notification_data_mock.call_count, 1)
