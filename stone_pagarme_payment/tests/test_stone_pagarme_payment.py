# Copyright 2024 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("stone_pagarme")
class TestStonePagarmePayment(TransactionCase):
    """Test Stone/Pagar.me payment provider functionality."""

    def setUp(self):
        super().setUp()
        
        # Create Stone/Pagar.me payment provider
        self.provider = self.env["payment.provider"].create({
            "name": "Stone/Pagar.me Test",
            "code": "stone_pagarme",
            "state": "test",
            "is_published": True,
            "stone_pagarme_api_key": "test_api_key",
            "stone_pagarme_encryption_key": "test_encryption_key",
        })
        
        # Create test partner with Brazilian data
        self.partner = self.env["res.partner"].create({
            "name": "Test Customer",
            "email": "test@example.com",
            "phone": "11987654321",
            "street": "Rua das Flores, 123",
            "city": "São Paulo",
            "zip": "01234567",
            "country_id": self.env.ref("base.br").id,
            "state_id": self.env.ref("base.state_br_sp").id,
        })
        
        # Add CPF to partner if l10n_br_base is available
        if hasattr(self.partner, "cnpj_cpf"):
            self.partner.cnpj_cpf = "12345678901"

    def test_provider_configuration(self):
        """Test provider configuration and basic settings."""
        self.assertEqual(self.provider.code, "stone_pagarme")
        self.assertTrue(self.provider.stone_pagarme_api_key)
        self.assertTrue(self.provider.stone_pagarme_encryption_key)
        
        # Test webhook URL computation
        self.provider._compute_stone_pagarme_webhook_url()
        self.assertIn("/payment/stone_pagarme/webhook", self.provider.stone_pagarme_webhook_url)

    def test_supported_currencies(self):
        """Test that only BRL currency is supported."""
        brl = self.env["res.currency"].search([("name", "=", "BRL")])
        supported = self.provider._get_supported_currencies()
        
        if brl:
            self.assertIn(brl, supported)
        
        # Test that non-BRL currencies are filtered out in compatibility check
        usd = self.env["res.currency"].search([("name", "=", "USD")])
        if usd:
            providers = self.env["payment.provider"]._get_compatible_providers(
                currency_id=usd.id
            )
            stone_providers = providers.filtered(lambda p: p.code == "stone_pagarme")
            self.assertFalse(stone_providers)

    def test_customer_data_preparation(self):
        """Test customer data preparation for Stone/Pagar.me API."""
        customer_data = self.provider._prepare_stone_pagarme_customer_data(self.partner)
        
        self.assertEqual(customer_data["name"], "Test Customer")
        self.assertEqual(customer_data["email"], "test@example.com")
        self.assertIn("address", customer_data)
        self.assertEqual(customer_data["address"]["city"], "São Paulo")
        
        # Test phone formatting
        if "phones" in customer_data:
            self.assertIn("home_phone", customer_data["phones"])

    def test_order_data_preparation(self):
        """Test order data preparation for Stone/Pagar.me API."""
        tx_values = {
            "amount": 100.00,
            "currency_id": self.env.ref("base.BRL").id,
            "reference": "TEST-001",
            "partner_id": self.partner.id,
        }
        
        order_data = self.provider._prepare_stone_pagarme_order_data(tx_values)
        
        self.assertEqual(order_data["amount"], 10000)  # 100.00 * 100 cents
        self.assertEqual(order_data["currency"], "BRL")
        self.assertIn("items", order_data)
        self.assertTrue(len(order_data["items"]) > 0)

    def test_transaction_creation(self):
        """Test payment transaction creation."""
        # Create a payment transaction
        transaction = self.env["payment.transaction"].create({
            "reference": "TEST-TX-001",
            "provider_id": self.provider.id,
            "partner_id": self.partner.id,
            "amount": 150.00,
            "currency_id": self.env.ref("base.BRL").id,
        })
        
        self.assertEqual(transaction.provider_code, "stone_pagarme")
        self.assertEqual(transaction.amount, 150.00)

    def test_transaction_request_preparation(self):
        """Test transaction request preparation."""
        transaction = self.env["payment.transaction"].create({
            "reference": "TEST-TX-002",
            "provider_id": self.provider.id,
            "partner_id": self.partner.id,
            "amount": 200.00,
            "currency_id": self.env.ref("base.BRL").id,
        })
        
        # Test transaction request data structure
        request_data = transaction._stone_pagarme_create_transaction_request()
        
        self.assertEqual(request_data["amount"], 20000)  # 200.00 * 100 cents
        self.assertIn("customer", request_data)
        self.assertIn("payment", request_data)
        self.assertIn("items", request_data)
        self.assertIn("metadata", request_data)
        
        # Test metadata
        metadata = request_data["metadata"]
        self.assertEqual(metadata["odoo_reference"], "TEST-TX-002")
        self.assertEqual(metadata["odoo_partner_id"], str(self.partner.id))

    @patch("requests.post")
    def test_api_request_method(self, mock_post):
        """Test API request method with mocked response."""
        # Mock successful API response
        mock_response = mock_post.return_value
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"id": "tx_123", "status": "pending"}
        
        # Test API request
        result = self.provider._stone_pagarme_make_request("test", {"data": "test"})
        
        self.assertEqual(result["id"], "tx_123")
        self.assertEqual(result["status"], "pending")
        mock_post.assert_called_once()

    def test_rendering_values(self):
        """Test rendering values for frontend."""
        transaction = self.env["payment.transaction"].create({
            "reference": "TEST-TX-003",
            "provider_id": self.provider.id,
            "partner_id": self.partner.id,
            "amount": 75.00,
            "currency_id": self.env.ref("base.BRL").id,
        })
        
        rendering_values = transaction._get_specific_rendering_values({})
        
        if transaction.provider_code == "stone_pagarme":
            self.assertIn("encryption_key", rendering_values)
            self.assertIn("return_url", rendering_values)
            self.assertIn("webhook_url", rendering_values)
            self.assertEqual(rendering_values["reference"], "TEST-TX-003")