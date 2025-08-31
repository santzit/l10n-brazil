# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class PagarmeBasicInstallTest(TransactionCase):
    """Minimal test to verify module installation and basic functionality."""

    def test_module_is_installed(self):
        """Verify the module is properly installed."""
        module = self.env["ir.module.module"].search(
            [("name", "=", "l10n_br_payment_pagarme")]
        )
        self.assertTrue(module, "l10n_br_payment_pagarme module should be installed")
        self.assertEqual(
            module.state, "installed", "Module should be in installed state"
        )

    def test_payment_provider_model_exists(self):
        """Verify payment provider model is available."""
        self.assertIn(
            "payment.provider", self.env, "payment.provider model should be available"
        )

    def test_pagarme_code_in_selection(self):
        """Verify pagarme is available as provider code."""
        provider_model = self.env["payment.provider"]
        provider_codes = provider_model._fields["code"].selection
        pagarme_codes = [code for code, name in provider_codes if code == "pagarme"]
        self.assertEqual(
            len(pagarme_codes),
            1,
            "pagarme should be available as provider code exactly once",
        )

    def test_simple_provider_creation(self):
        """Test basic provider creation without complex dependencies."""
        provider = self.env["payment.provider"].create(
            {
                "name": "Test Pagar.me Basic",
                "code": "pagarme",
                "state": "disabled",  # Keep disabled to avoid validation issues
                "pagarme_app_id": "test_app_id",
                "pagarme_api_key": "test_api_key",
            }
        )

        # Basic assertions
        self.assertTrue(provider.id, "Provider should be created successfully")
        self.assertEqual(provider.code, "pagarme", "Provider code should be pagarme")
        self.assertEqual(
            provider.pagarme_app_id, "test_app_id", "App ID should be set correctly"
        )

    def test_transparent_checkout_configuration(self):
        """Test that provider is configured for transparent checkout by default."""
        provider = self.env["payment.provider"].create(
            {
                "name": "Test Transparent Checkout",
                "code": "pagarme",
                "state": "test",
                "pagarme_app_id": "test_app_id",
                "pagarme_api_key": "test_api_key",
            }
        )

        # Test inline form configuration
        self.assertTrue(
            provider._should_build_inline_form(),
            "Provider should support inline forms for transparent checkout",
        )

        # Test that inline form view is configured
        self.assertTrue(
            provider.inline_form_view_id,
            "Provider should have inline form view configured",
        )

        # Test that redirect form view is not used
        self.assertFalse(
            provider.redirect_form_view_id,
            "Provider should not use redirect form for transparent checkout",
        )
