# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.l10n_br_payment_pagarme.tests.common import PagarmeCommon
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
        provider = self.env["payment.provider"].create({
            "name": "Test Pagar.me",
            "code": "pagarme",
            "state": "test",
            "pagarme_app_id": "test_app_id",
            "pagarme_api_key": "test_api_key",
        })
        self.assertEqual(provider.code, "pagarme")
        self.assertEqual(provider.pagarme_app_id, "test_app_id")


@tagged("post_install", "-at_install")
class PagarmeTest(PagarmeCommon, PaymentHttpCommon):
    def test_module_basic_structure(self):
        """Test basic module structure and imports work correctly."""
        # This should always pass if the module is installed correctly
        self.assertTrue(True, "Basic test to ensure test discovery works")
        
        # Test that we can import the main provider model
        provider_model = self.env["payment.provider"]
        self.assertTrue(provider_model, "payment.provider model should be available")
        
        # Test that pagarme is available as a provider code
        provider_codes = provider_model._fields["code"].selection
        pagarme_codes = [code for code, name in provider_codes if code == "pagarme"]
        self.assertTrue(pagarme_codes, "pagarme should be available as provider code")

    def test_processing_values(self):
        """Test that processing values are correctly generated."""
        tx = self._create_transaction(flow="direct")
        processing_values = tx._get_specific_processing_values({})

        self.assertEqual(processing_values["public_key"], self.pagarme.pagarme_app_id)
        self.assertEqual(processing_values["amount"], int(self.amount * 100))
        self.assertEqual(processing_values["currency"], self.currency.name.lower())

    def test_provider_webhook_url_generation(self):
        """Test that webhook URL is correctly generated."""
        webhook_url = self.pagarme._get_pagarme_webhook_url()
        expected_url = f"{self.pagarme.get_base_url()}/payment/pagarme/webhook"
        self.assertEqual(webhook_url, expected_url)

    def test_provider_default_payment_methods(self):
        """Test that default payment method codes include card for Pagar.me."""
        payment_methods = self.pagarme._get_default_payment_method_codes()
        self.assertIn("card", payment_methods)

    @mute_logger("odoo.addons.l10n_br_payment_pagarme.models.payment_transaction")
    def test_send_payment_request_success(self):
        """Test successful payment request."""
        tx = self._create_transaction("direct", state="draft")
        tx.pagarme_token = "card_test_1234567890"

        mock_response = {
            "id": "or_test_1234567890",
            "status": "paid",
            "amount": int(self.amount * 100),
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status.return_value = None

            tx._send_payment_request()

        self.assertEqual(tx.state, "done")
        self.assertEqual(tx.provider_reference, "or_test_1234567890")

    @mute_logger("odoo.addons.l10n_br_payment_pagarme.models.payment_transaction")
    def test_send_payment_request_pending(self):
        """Test pending payment request."""
        tx = self._create_transaction("direct", state="draft")
        tx.pagarme_token = "card_test_1234567890"

        mock_response = {
            "id": "or_test_pending_1234567890",
            "status": "pending",
            "amount": int(self.amount * 100),
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status.return_value = None

            tx._send_payment_request()

        self.assertEqual(tx.state, "pending")
        self.assertEqual(tx.provider_reference, "or_test_pending_1234567890")

    @mute_logger("odoo.addons.l10n_br_payment_pagarme.models.payment_transaction")
    def test_send_payment_request_failed(self):
        """Test failed payment request."""
        tx = self._create_transaction("direct", state="draft")
        tx.pagarme_token = "card_test_1234567890"

        mock_response = {
            "id": "or_test_failed_1234567890",
            "status": "failed",
            "amount": int(self.amount * 100),
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status.return_value = None

            tx._send_payment_request()

        self.assertEqual(tx.state, "error")

    @mute_logger("odoo.addons.l10n_br_payment_pagarme.models.payment_transaction")
    def test_process_notification_data_paid(self):
        """Test processing of successful payment notification."""
        tx = self._create_transaction("direct", state="pending")

        tx._process_notification_data(self.notification_data)

        self.assertEqual(tx.state, "done")

    @mute_logger("odoo.addons.l10n_br_payment_pagarme.models.payment_transaction")
    def test_process_notification_data_failed(self):
        """Test processing of failed payment notification."""
        tx = self._create_transaction("direct", state="pending")

        tx._process_notification_data(self.failed_notification_data)

        self.assertEqual(tx.state, "error")

    @mute_logger("odoo.addons.l10n_br_payment_pagarme.models.payment_transaction")
    def test_process_notification_data_canceled(self):
        """Test processing of canceled payment notification."""
        tx = self._create_transaction("direct", state="pending")

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

    def test_transaction_pagarme_token_field(self):
        """Test that transaction has pagarme_token field."""
        tx = self._create_transaction("direct")
        self.assertTrue(hasattr(tx, "pagarme_token"))

        # Test setting and getting token
        test_token = "card_test_token_1234567890"
        tx.pagarme_token = test_token
        self.assertEqual(tx.pagarme_token, test_token)

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

        # Test webhook URL generation
        webhook_url = provider._get_pagarme_webhook_url()
        self.assertIn("/payment/pagarme/webhook", webhook_url)

    def test_inline_form_configuration(self):
        """Test that the inline form is properly configured for transparent checkout."""
        # Test that inline_form_view_id is set
        self.assertTrue(self.pagarme.inline_form_view_id)

        # Test that redirect_form_view_id is False (indicating transparent checkout)
        self.assertFalse(self.pagarme.redirect_form_view_id)

        # Test that the inline form template exists
        inline_template = self.env.ref("l10n_br_payment_pagarme.inline_form")
        self.assertEqual(self.pagarme.inline_form_view_id, inline_template)

        # Test that _should_build_inline_form returns True for direct payments
        self.assertTrue(self.pagarme._should_build_inline_form(is_validation=False))
        self.assertTrue(self.pagarme._should_build_inline_form(is_validation=True))

    def test_should_build_inline_form_method(self):
        """Test that _should_build_inline_form method is implemented correctly."""
        # For Pagar.me provider, should always return True for inline forms
        self.assertTrue(self.pagarme._should_build_inline_form())
        self.assertTrue(self.pagarme._should_build_inline_form(is_validation=True))
        self.assertTrue(self.pagarme._should_build_inline_form(is_validation=False))

        # For other providers, should call super method
        other_provider = self.env["payment.provider"].create(
            {
                "name": "Other Provider",
                "code": "other",
                "state": "test",
            }
        )
        # This should call the default implementation
        result = other_provider._should_build_inline_form()
        # Default implementation returns True
        self.assertTrue(result)

    def test_inline_form_template_structure(self):
        """Test that the inline form template has the correct structure."""
        # Get the template
        template = self.env.ref("l10n_br_payment_pagarme.inline_form")
        self.assertTrue(template)

        # Check template arch contains the required form elements
        template_arch = template.arch

        # Check for required input fields (payment_demo pattern)
        self.assertIn("card_holder_name", template_arch)
        self.assertIn("card_number", template_arch)
        self.assertIn("card_expiry_month", template_arch)
        self.assertIn("card_expiry_year", template_arch)
        self.assertIn("card_cvv", template_arch)

        # Check for Pagar.me data attributes
        self.assertIn('data-pagarme-checkout-element="cardholder-name"', template_arch)
        self.assertIn('data-pagarme-checkout-element="card-number"', template_arch)
        self.assertIn(
            'data-pagarme-checkout-element="card-expiry-month"', template_arch
        )
        self.assertIn('data-pagarme-checkout-element="card-expiry-year"', template_arch)
        self.assertIn('data-pagarme-checkout-element="card-cvv"', template_arch)

    def test_direct_payment_flow_creation(self):
        """Test that transactions can be created for direct payment flow."""
        tx = self._create_transaction(flow="direct", state="draft")

        # Test that the transaction is configured for direct payment
        self.assertEqual(tx.operation, "online_direct")

        # Test processing values for direct payment
        processing_values = tx._get_specific_processing_values({})
        self.assertEqual(processing_values["public_key"], self.pagarme.pagarme_app_id)

    def test_transparent_checkout_configuration(self):
        """Test that the provider is configured for transparent checkout."""
        # Test that the provider supports direct payment (transparent checkout)
        self.assertIn("card", self.pagarme._get_default_payment_method_codes())

        # Test that tokenization support is correctly configured
        self.assertFalse(self.pagarme.support_tokenization)
        self.assertFalse(self.pagarme.support_express_checkout)

        # Test refund support
        self.assertEqual(self.pagarme.support_refund, "partial")

    def test_provider_display_configuration(self):
        """Test that the provider display configuration is correct for inline form."""
        # Test display properties
        self.assertEqual(self.pagarme.display_as, "💳 Pagar.me")
        self.assertIn("segurança", self.pagarme.pre_msg.lower())

        # Test that messages are in Portuguese (Brazilian localization)
        self.assertIn("processado com sucesso", self.pagarme.done_msg.lower())
        self.assertIn("processando", self.pagarme.pending_msg.lower())
        self.assertIn("cancelado", self.pagarme.cancel_msg.lower())

        # Test provider state and publishing
        # Should not be enabled by default
        self.assertIn(self.pagarme.state, ["test", "disabled"])

        # Test that the provider has the correct configuration for transparent checkout
        # These are the key fields that determine inline vs redirect behavior
        self.assertTrue(
            self.pagarme.inline_form_view_id,
            "inline_form_view_id must be set for transparent checkout",
        )
        self.assertFalse(
            self.pagarme.redirect_form_view_id,
            "redirect_form_view_id must be False for transparent checkout",
        )

        # Test support fields are configured correctly for transparent checkout
        self.assertFalse(
            self.pagarme.support_tokenization,
            "Tokenization should be disabled for transparent checkout",
        )
        self.assertFalse(
            self.pagarme.support_express_checkout, "Express checkout should be disabled"
        )
        self.assertEqual(
            self.pagarme.support_refund, "partial", "Should support partial refunds"
        )

    def test_transparent_vs_redirect_configuration(self):
        """Test provider configured for transparent (inline) vs redirect."""
        # Test the key method that determines if inline form should be built
        should_build_inline = self.pagarme._should_build_inline_form()
        self.assertTrue(
            should_build_inline,
            "_should_build_inline_form must return True for transparent checkout",
        )

        # Test template references
        self.assertIsNotNone(
            self.pagarme.inline_form_view_id,
            "Inline form template is required for transparent checkout",
        )
        self.assertIsNone(
            self.pagarme.redirect_form_view_id,
            "Redirect form template must be None for transparent checkout",
        )

        # Test that the template actually exists and is accessible
        try:
            template = self.env.ref("l10n_br_payment_pagarme.inline_form")
            self.assertTrue(template, "Inline form template must exist")
            self.assertEqual(template.type, "qweb", "Template must be a QWeb template")
        except Exception as e:
            self.fail(f"Inline form template is not accessible: {e}")

        # Test provider selection logic would include this provider for inline payments
        # This simulates the logic Odoo uses to determine available payment providers
        compatible_providers = self.env["payment.provider"]._get_compatible_providers(
            company_id=self.env.company.id,
            partner_id=self.partner.id,
            amount=100.0,
            currency_id=self.currency.id,
            force_tokenization=False,
            is_express_checkout=False,
            is_validation=False,
        )

        # The provider should be compatible (if enabled/test mode)
        if self.pagarme.state in ["enabled", "test"]:
            self.assertIn(
                self.pagarme,
                compatible_providers,
                "Provider should be compatible for direct payments",
            )
