# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.l10n_br_payment_pagarme.tests.common import PagarmeCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon


@tagged("post_install", "-at_install")
class PagarmeTest(PagarmeCommon, PaymentHttpCommon):
    def test_processing_values(self):
        """Test that processing values are correctly generated."""
        tx = self._create_transaction(flow="redirect")

        # Mock the checkout session creation
        with patch.object(
            tx.provider_id, "_create_pagarme_checkout_session"
        ) as mock_create_session:
            mock_create_session.return_value = (
                "https://checkout.pagar.me/checkout/test_123"
            )

            processing_values = tx._get_specific_processing_values({})

            self.assertEqual(
                processing_values["checkout_url"],
                "https://checkout.pagar.me/checkout/test_123",
            )
            mock_create_session.assert_called_once_with(tx)

    def test_provider_return_url_generation(self):
        """Test that return URL is correctly generated."""
        reference = "test_tx_ref_12345"
        return_url = self.pagarme._get_return_url(reference)
        expected_url = (
            f"{self.pagarme.get_base_url()}/payment/pagarme/return"
            f"?reference={reference}"
        )
        self.assertEqual(return_url, expected_url)

    def test_provider_webhook_url_generation(self):
        """Test that webhook URL is correctly generated."""
        webhook_url = self.pagarme._get_pagarme_webhook_url()
        expected_url = f"{self.pagarme.get_base_url()}/payment/pagarme/webhook"
        self.assertEqual(webhook_url, expected_url)

    def test_provider_default_payment_methods(self):
        """Test that default payment method codes include card for Pagar.me."""
        payment_methods = self.pagarme._get_default_payment_method_codes()
        self.assertIn("card", payment_methods)

    @mute_logger("odoo.addons.l10n_br_payment_pagarme.models.payment_provider")
    def test_create_checkout_session_success(self):
        """Test successful checkout session creation."""
        tx = self._create_transaction("redirect", state="draft")

        mock_response = {
            "id": "or_test_1234567890",
            "checkout": {"url": "https://checkout.pagar.me/checkout/test_123"},
            "status": "pending",
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status.return_value = None

            checkout_url = self.pagarme._create_pagarme_checkout_session(tx)

        self.assertEqual(checkout_url, "https://checkout.pagar.me/checkout/test_123")
        self.assertEqual(tx.provider_reference, "or_test_1234567890")

    def test_get_tx_from_notification_data(self):
        """Test finding transaction from notification data."""
        tx = self._create_transaction("redirect", state="pending")
        tx.provider_reference = "or_test_1234567890"

        # Test finding by provider_reference
        notification_data = {"id": "or_test_1234567890", "status": "paid"}
        found_tx = tx._get_tx_from_notification_data("pagarme", notification_data)
        self.assertEqual(found_tx, tx)

        # Test finding by metadata reference
        tx2 = self._create_transaction("redirect", state="pending")
        notification_data2 = {
            "id": "or_test_9876543210",
            "metadata": {"odoo_reference": tx2.reference},
            "status": "paid",
        }
        found_tx2 = tx2._get_tx_from_notification_data("pagarme", notification_data2)
        self.assertEqual(found_tx2, tx2)

    @mute_logger("odoo.addons.l10n_br_payment_pagarme.models.payment_transaction")
    def test_process_notification_data_paid(self):
        """Test processing of successful payment notification."""
        tx = self._create_transaction("redirect", state="pending")

        tx._process_notification_data(self.notification_data)

        self.assertEqual(tx.state, "done")

    @mute_logger("odoo.addons.l10n_br_payment_pagarme.models.payment_transaction")
    def test_process_notification_data_failed(self):
        """Test processing of failed payment notification."""
        tx = self._create_transaction("redirect", state="pending")

        tx._process_notification_data(self.failed_notification_data)

        self.assertEqual(tx.state, "error")

    @mute_logger("odoo.addons.l10n_br_payment_pagarme.models.payment_transaction")
    def test_process_notification_data_canceled(self):
        """Test processing of canceled payment notification."""
        tx = self._create_transaction("redirect", state="pending")

        canceled_data = dict(self.notification_data, status="canceled")
        tx._process_notification_data(canceled_data)

        self.assertEqual(tx.state, "cancel")

    def test_provider_configuration_fields(self):
        """Test that provider configuration fields are properly set."""
        self.assertTrue(hasattr(self.pagarme, "pagarme_app_id"))
        self.assertTrue(hasattr(self.pagarme, "pagarme_api_key"))
        self.assertEqual(self.pagarme.pagarme_app_id, "app_test_1234567890")
        self.assertEqual(
            self.pagarme.pagarme_api_key, "sk_test_abcdef1234567890abcdef1234567890"
        )

    def test_provider_code_selection(self):
        """Test that Pagar.me is available as a provider option."""
        provider_codes = self.env["payment.provider"]._fields["code"].selection
        pagarme_option = next(
            (option for option in provider_codes if option[0] == "pagarme"), None
        )
        self.assertIsNotNone(pagarme_option)
        self.assertEqual(pagarme_option[1], "Pagar.me")

    def test_transaction_pagarme_order_id_field(self):
        """Test that transaction has pagarme_order_id field."""
        tx = self._create_transaction("redirect")
        self.assertTrue(hasattr(tx, "pagarme_order_id"))

        # Test setting and getting order ID
        test_order_id = "or_test_order_1234567890"
        tx.pagarme_order_id = test_order_id
        self.assertEqual(tx.pagarme_order_id, test_order_id)

    def test_module_installation(self):
        """Test that the module can be properly installed and configured."""
        # Test that the provider can be created
        provider = self.env["payment.provider"].create(
            {
                "name": "Test Pagar.me Provider",
                "code": "pagarme",
                "state": "test",
                "pagarme_app_id": "test_app_id",
                "pagarme_api_key": "test_api_key",
            }
        )

        self.assertEqual(provider.code, "pagarme")
        self.assertEqual(provider.pagarme_app_id, "test_app_id")
        self.assertEqual(provider.pagarme_api_key, "test_api_key")

        # Test return URL generation
        return_url = provider._get_return_url("test_ref")
        self.assertIn("/payment/pagarme/return", return_url)
