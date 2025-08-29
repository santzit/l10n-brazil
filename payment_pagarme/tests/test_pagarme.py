# Copyright 2024 OCA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch, MagicMock

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestPagarme(TransactionCase):

    def setUp(self):
        super().setUp()
        self.acquirer = self.env["payment.acquirer"].create({
            "name": "Test Pagar.me",
            "provider": "pagarme",
            "pagarme_app_id": "pk_test_123456",
            "pagarme_api_key": "sk_test_123456",
            "state": "test",
        })
        self.partner = self.env["res.partner"].create({
            "name": "Test Partner",
            "email": "test@example.com",
            "phone": "11999999999",
        })

    def test_acquirer_creation(self):
        """Test that Pagar.me acquirer can be created."""
        self.assertEqual(self.acquirer.provider, "pagarme")
        self.assertEqual(self.acquirer.pagarme_app_id, "pk_test_123456")
        self.assertEqual(self.acquirer.pagarme_api_key, "sk_test_123456")

    def test_webhook_url_computation(self):
        """Test webhook URL computation."""
        self.acquirer._compute_pagarme_webhook_url()
        self.assertTrue(self.acquirer.pagarme_webhook_url.endswith("/payment/pagarme/webhook"))

    def test_credentials_validation(self):
        """Test credentials validation."""
        # Test missing app_id
        with self.assertRaises(ValidationError):
            self.env["payment.acquirer"].create({
                "name": "Invalid Pagar.me",
                "provider": "pagarme",
                "pagarme_api_key": "sk_test_123456",
                "state": "test",
            })
        
        # Test missing api_key
        with self.assertRaises(ValidationError):
            self.env["payment.acquirer"].create({
                "name": "Invalid Pagar.me",
                "provider": "pagarme",
                "pagarme_app_id": "pk_test_123456",
                "state": "test",
            })

    def test_transaction_creation(self):
        """Test transaction creation."""
        tx = self.env["payment.transaction"].create({
            "reference": "TEST-001",
            "acquirer_id": self.acquirer.id,
            "partner_id": self.partner.id,
            "amount": 100.0,
            "currency_id": self.env.ref("base.BRL").id,
        })
        
        self.assertEqual(tx.acquirer_id, self.acquirer)
        self.assertEqual(tx.amount, 100.0)

    @patch('requests.post')
    def test_pagarme_create_order(self, mock_post):
        """Test order creation with Pagar.me."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "ord_test_123456",
            "status": "pending",
            "charges": [{"id": "ch_test_123456", "status": "pending"}]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        tx = self.env["payment.transaction"].create({
            "reference": "TEST-002", 
            "acquirer_id": self.acquirer.id,
            "partner_id": self.partner.id,
            "amount": 150.0,
            "currency_id": self.env.ref("base.BRL").id,
            "pagarme_token": "tok_test_123456",
        })
        
        result = tx._pagarme_create_order({"token": "tok_test_123456"})
        
        self.assertEqual(result["id"], "ord_test_123456")
        self.assertEqual(tx.pagarme_order_id, "ord_test_123456")
        self.assertEqual(tx.pagarme_charge_id, "ch_test_123456")

    def test_webhook_processing(self):
        """Test webhook data processing."""
        tx = self.env["payment.transaction"].create({
            "reference": "TEST-003",
            "acquirer_id": self.acquirer.id,
            "partner_id": self.partner.id,
            "amount": 200.0,
            "currency_id": self.env.ref("base.BRL").id,
            "pagarme_order_id": "ord_test_webhook",
        })
        
        # Test paid status
        webhook_data = {
            "id": "ord_test_webhook",
            "status": "paid",
            "charges": [{"id": "ch_test_webhook", "status": "paid"}]
        }
        
        tx._pagarme_process_webhook_data(webhook_data)
        self.assertEqual(tx.state, "done")

    def test_form_values_generation(self):
        """Test form values generation."""
        values = {
            "reference": "TEST-004",
            "amount": 300.0,
            "currency": "BRL",
            "partner_name": "Test Customer",
            "partner_email": "customer@test.com",
        }
        
        result = self.acquirer.pagarme_form_generate_values(values)
        
        self.assertEqual(result["app_id"], "pk_test_123456")
        self.assertEqual(result["amount"], 30000)  # Converted to cents
        self.assertEqual(result["currency"], "BRL")
        self.assertTrue(result["return_url"].endswith("/payment/pagarme/return"))

    def test_default_payment_method_codes(self):
        """Test default payment method codes."""
        codes = self.acquirer._get_default_payment_method_codes()
        self.assertIn("card", codes)