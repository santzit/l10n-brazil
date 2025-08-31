# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.l10n_br_payment_pagarme.tests.common import PaymentPagarmeCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon


@tagged("-at_install", "post_install")
class TestPaymentTransaction(PaymentPagarmeCommon, PaymentHttpCommon):
    def test_processing_notification_data_sets_transaction_pending(self):
        """Test that the transaction state is set to 'pending' when the notification
        data indicate a pending payment."""
        tx = self._create_transaction("direct", reference=f"{self.reference}-pending")
        pending_data = {
            "status": "pending",
            "charges": [{"status": "pending"}],
            "reference": tx.reference,
        }
        tx._process_notification_data(pending_data)
        self.assertEqual(tx.state, "pending")

    def test_processing_notification_data_authorizes_transaction(self):
        """Test that the transaction state is set to 'authorize' when the
        notification data indicate a successful payment and manual capture is
        enabled."""
        self.provider.capture_manually = True
        tx = self._create_transaction("direct", reference=f"{self.reference}-authorize")
        paid_data = {
            "status": "paid",
            "charges": [{"status": "paid"}],
            "reference": tx.reference,
        }
        tx._process_notification_data(paid_data)
        self.assertEqual(tx.state, "authorized")

    def test_processing_notification_data_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the notification
        data indicate a successful payment."""
        tx = self._create_transaction("direct", reference=f"{self.reference}-done")
        paid_data = {
            "status": "paid",
            "charges": [{"status": "paid"}],
            "reference": tx.reference,
        }
        tx._process_notification_data(paid_data)
        self.assertEqual(tx.state, "done")

    def test_processing_notification_data_cancels_transaction(self):
        """Test that the transaction state is set to 'cancel' when the notification
        data indicate an unsuccessful payment."""
        tx = self._create_transaction("direct", reference=f"{self.reference}-cancel")
        canceled_data = {
            "type": "order.canceled",
            "data": {},
            "reference": tx.reference,
        }
        tx._process_notification_data(canceled_data)
        self.assertEqual(tx.state, "cancel")

    def test_processing_notification_data_sets_transaction_in_error(self):
        """Test that the transaction state is set to 'error' when the notification
        data indicate an error during the payment."""
        tx = self._create_transaction("direct", reference=f"{self.reference}-error")
        failed_data = {
            "status": "failed",
            "charges": [{"status": "failed"}],
            "reference": tx.reference,
        }
        tx._process_notification_data(failed_data)
        self.assertEqual(tx.state, "error")

    def test_processing_webhook_paid_event(self):
        """Test that webhook paid event sets transaction to done."""
        tx = self._create_transaction(
            "direct", reference=f"{self.reference}-webhook-paid"
        )
        webhook_data = {
            "type": "order.paid",
            "data": {"id": "order_123"},
            "reference": tx.reference,
        }
        tx._process_notification_data(webhook_data)
        self.assertEqual(tx.state, "done")

    def test_processing_webhook_failed_event(self):
        """Test that webhook failed event sets transaction to error."""
        tx = self._create_transaction(
            "direct", reference=f"{self.reference}-webhook-failed"
        )
        webhook_data = {
            "type": "order.payment_failed",
            "data": {"reason": "Card declined"},
            "reference": tx.reference,
        }
        tx._process_notification_data(webhook_data)
        self.assertEqual(tx.state, "error")

    @mute_logger("odoo.addons.l10n_br_payment_pagarme.models.payment_transaction")
    def test_send_payment_request_with_token(self):
        """Test that payment request is sent successfully when token is provided."""
        tx = self._create_transaction(
            "direct", reference=f"{self.reference}-payment", state="draft"
        )
        tx.pagarme_token = "card_test_1234567890"

        mock_response = {
            "id": "or_test_1234567890",
            "status": "paid",
            "charges": [{"status": "paid"}],
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status.return_value = None

            tx._send_payment_request()

        self.assertEqual(tx.state, "done")
        self.assertEqual(tx.provider_reference, "or_test_1234567890")
