# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.l10n_br_payment_pagarme.tests.common import PaymentPagarmeCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon


@tagged("post_install", "-at_install")
class PagarmeBasicTest(TransactionCase):
    """Basic tests that should always run to verify test discovery."""

    def test_module_installed(self):
        """Test that the module is properly installed."""
        # Test that the module is available
        module = self.env["ir.module.module"].search(
            [("name", "=", "l10n_br_payment_pagarme")]
        )
        self.assertTrue(module, "l10n_br_payment_pagarme module should be found")

        # Test that payment provider model is available
        provider_model = self.env["payment.provider"]
        self.assertTrue(provider_model, "payment.provider model should be available")

    def test_pagarme_provider_code_available(self):
        """Test that pagarme is available as a provider code."""
        provider_model = self.env["payment.provider"]
        provider_codes = provider_model._fields["code"].selection
        pagarme_codes = [code for code, name in provider_codes if code == "pagarme"]
        self.assertEqual(
            len(pagarme_codes), 1, "pagarme should be available as provider code"
        )

    def test_provider_creation(self):
        """Test that a Pagar.me provider can be created."""
        provider = self.env["payment.provider"].create(
            {
                "name": "Test Pagar.me",
                "code": "pagarme",
                "state": "test",
                "pagarme_app_id": "test_app_id",
                "pagarme_api_key": "test_api_key",
            }
        )
        self.assertEqual(provider.code, "pagarme")
        self.assertEqual(provider.pagarme_app_id, "test_app_id")


@tagged("post_install", "-at_install")
class PagarmeTest(PaymentPagarmeCommon, PaymentHttpCommon):
    """Essential Pagar.me functionality tests following demo pattern."""

    def test_processing_values(self):
        """Test that processing values are correctly generated."""
        tx = self._create_transaction(
            flow="direct", reference=f"{self.reference}-values"
        )
        processing_values = tx._get_specific_processing_values({})

        self.assertEqual(processing_values["public_key"], self.provider.pagarme_app_id)
        self.assertEqual(processing_values["amount"], int(self.amount * 100))
        self.assertEqual(processing_values["currency"], self.currency.name.lower())

    def test_provider_webhook_url_generation(self):
        """Test that webhook URL is correctly generated."""
        webhook_url = self.provider._get_pagarme_webhook_url()
        expected_url = f"{self.provider.get_base_url()}/payment/pagarme/webhook"
        self.assertEqual(webhook_url, expected_url)

    @mute_logger("odoo.addons.l10n_br_payment_pagarme.models.payment_transaction")
    def test_send_payment_request_success(self):
        """Test successful payment request."""
        tx = self._create_transaction(
            "direct", reference=f"{self.reference}-success", state="draft"
        )
        tx.pagarme_token = "card_test_1234567890"

        mock_response = {
            "id": "or_test_1234567890",
            "status": "paid",
            "amount": int(self.amount * 100),
            "charges": [
                {
                    "id": "charge_test_123",
                    "status": "paid",
                    "amount": int(self.amount * 100),
                }
            ],
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status.return_value = None

            tx._send_payment_request()

        self.assertEqual(tx.state, "done")
        self.assertEqual(tx.provider_reference, "or_test_1234567890")

    def test_inline_form_configuration(self):
        """Test that the inline form is properly configured for transparent checkout."""
        # Test that inline_form_view_id is set
        self.assertTrue(self.provider.inline_form_view_id)

        # Test that redirect_form_view_id is False (indicating transparent checkout)
        self.assertFalse(self.provider.redirect_form_view_id)

        # Test that the inline form template exists
        inline_template = self.env.ref("l10n_br_payment_pagarme.inline_form")
        self.assertEqual(self.provider.inline_form_view_id, inline_template)
