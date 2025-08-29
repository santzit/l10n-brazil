# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPagarme(TransactionCase):

    def setUp(self):
        super().setUp()
        self.currency_brl = self.env["res.currency"].search([("name", "=", "BRL")], limit=1)
        if not self.currency_brl:
            self.currency_brl = self.env["res.currency"].create({
                "name": "BRL",
                "symbol": "R$",
                "position": "before",
                "rounding": 0.01,
            })
        
        self.acquirer = self.env["payment.acquirer"].create({
            "name": "Pagar.me Test",
            "provider": "pagarme",
            "state": "test",
            "pagarme_api_key": "sk_test_xxxxx",
            "pagarme_encryption_key": "ek_test_xxxxx",
        })
        
        self.partner = self.env["res.partner"].create({
            "name": "Test Partner",
            "email": "test@example.com",
            "vat": "12345678901",
        })

    def test_pagarme_acquirer_creation(self):
        """Test that Pagar.me acquirer can be created"""
        self.assertEqual(self.acquirer.provider, "pagarme")
        self.assertEqual(self.acquirer.state, "test")
        self.assertTrue(self.acquirer.pagarme_api_key)

    def test_currency_compatibility(self):
        """Test that Pagar.me only supports BRL currency"""
        compatible = self.acquirer._get_compatible_acquirers(
            currency_id=self.currency_brl.id
        )
        self.assertIn(self.acquirer, compatible)
        
        # Test with non-BRL currency
        currency_usd = self.env["res.currency"].search([("name", "=", "USD")], limit=1)
        if currency_usd:
            compatible_usd = self.acquirer._get_compatible_acquirers(
                currency_id=currency_usd.id
            )
            # Should be filtered out for non-BRL currencies
            self.assertNotIn(self.acquirer, compatible_usd.filtered(lambda a: a.provider == "pagarme"))

    def test_api_url_generation(self):
        """Test API URL generation"""
        url = self.acquirer._pagarme_get_api_url()
        self.assertEqual(url, "https://api.pagar.me/core/v5")

    def test_payment_transaction_creation(self):
        """Test payment transaction creation"""
        transaction = self.env["payment.transaction"].create({
            "acquirer_id": self.acquirer.id,
            "reference": "TEST_TX_001",
            "amount": 100.0,
            "currency_id": self.currency_brl.id,
            "partner_id": self.partner.id,
            "pagarme_card_token": "tok_test_xxxxx",
        })
        
        self.assertEqual(transaction.acquirer_id, self.acquirer)
        self.assertEqual(transaction.amount, 100.0)
        self.assertTrue(transaction.pagarme_card_token)

    @patch("requests.post")
    def test_charge_creation(self, mock_post):
        """Test charge creation with Pagar.me API"""
        # Mock successful API response
        mock_post.return_value.json.return_value = {
            "id": "ch_test_123456",
            "status": "paid",
            "amount": 10000,  # in cents
        }
        mock_post.return_value.raise_for_status.return_value = None
        
        transaction_data = {
            "amount": 100.0,
            "reference": "TEST_TX_001",
            "partner_name": "Test Partner",
            "partner_email": "test@example.com",
            "partner_vat": "12345678901",
            "card_token": "tok_test_xxxxx",
        }
        
        result = self.acquirer._pagarme_create_charge(transaction_data)
        
        self.assertEqual(result["id"], "ch_test_123456")
        self.assertEqual(result["status"], "paid")
        mock_post.assert_called_once()

    def test_webhook_signature_validation(self):
        """Test webhook signature validation"""
        from ..controllers.main import PagarmeController
        
        controller = PagarmeController()
        payload = b'{"test": "data"}'
        secret = "test_secret"
        
        # Generate valid signature
        import hashlib
        import hmac
        signature = "sha256=" + hmac.new(
            secret.encode("utf-8"), 
            payload, 
            hashlib.sha256
        ).hexdigest()
        
        # Test valid signature
        self.assertTrue(controller._verify_webhook_signature(payload, signature, secret))
        
        # Test invalid signature
        self.assertFalse(controller._verify_webhook_signature(payload, "invalid", secret))

    def test_transaction_tokenization(self):
        """Test transaction tokenization"""
        transaction = self.env["payment.transaction"].create({
            "acquirer_id": self.acquirer.id,
            "reference": "TEST_TX_002",
            "amount": 50.0,
            "currency_id": self.currency_brl.id,
            "partner_id": self.partner.id,
        })
        
        # Test tokenization
        feedback_data = {"card_token": "tok_test_new_token"}
        transaction._pagarme_tokenize_from_feedback_data(feedback_data)
        
        self.assertEqual(transaction.pagarme_card_token, "tok_test_new_token")

    def test_webhook_processing(self):
        """Test webhook data processing"""
        transaction = self.env["payment.transaction"].create({
            "acquirer_id": self.acquirer.id,
            "reference": "TEST_TX_003",
            "amount": 75.0,
            "currency_id": self.currency_brl.id,
            "partner_id": self.partner.id,
            "pagarme_charge_id": "ch_test_webhook_123",
        })
        
        # Test successful payment webhook
        webhook_data = {
            "id": "ch_test_webhook_123",
            "status": "paid",
            "amount": 7500,
        }
        
        transaction._process_webhook_data(webhook_data)
        self.assertEqual(transaction.state, "done")
        
        # Test failed payment webhook
        webhook_data_failed = {
            "id": "ch_test_webhook_123",
            "status": "failed",
            "gateway_response": {"message": "Card declined"},
        }
        
        transaction.state = "pending"  # Reset state
        transaction._process_webhook_data(webhook_data_failed)
        self.assertEqual(transaction.state, "error")
        self.assertIn("Card declined", transaction.state_message)