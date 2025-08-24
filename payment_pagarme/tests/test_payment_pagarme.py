# Copyright 2024 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase


class TestPaymentPagarme(TransactionCase):
    
    def setUp(self):
        super().setUp()
        
        # Create a Pagar.me payment provider
        self.provider = self.env["payment.provider"].create({
            "name": "Pagar.me Test",
            "code": "pagarme",
            "state": "test",
            "is_published": True,
            "pagarme_api_key": "sk_test_example_key",
            "pagarme_encryption_key": "ek_test_example_key",
        })
        
        # Create a test partner
        self.partner = self.env["res.partner"].create({
            "name": "Test Customer",
            "email": "test@example.com",
            "cnpj_cpf": "12345678901",  # Valid CPF format
            "phone": "11999999999",
            "street": "Rua Teste, 123",
            "city": "São Paulo",
            "zip": "01234-567",
            "country_id": self.env.ref("base.br").id,
            "state_id": self.env.ref("base.state_br_sp").id,
        })

    def test_provider_creation(self):
        """Test that Pagar.me provider can be created."""
        self.assertEqual(self.provider.code, "pagarme")
        self.assertEqual(self.provider.state, "test")
        self.assertTrue(self.provider.pagarme_webhook_url)

    def test_customer_data_preparation(self):
        """Test customer data preparation for Pagar.me API."""
        customer_data = self.provider._prepare_pagarme_customer_data(self.partner)
        
        self.assertEqual(customer_data["name"], "Test Customer")
        self.assertEqual(customer_data["email"], "test@example.com")
        self.assertEqual(customer_data["document"], "12345678901")
        self.assertEqual(customer_data["document_type"], "cpf")
        self.assertEqual(customer_data["type"], "individual")

    def test_transaction_creation(self):
        """Test payment transaction creation."""
        transaction = self.env["payment.transaction"].create({
            "provider_id": self.provider.id,
            "reference": "TEST-001",
            "amount": 100.00,
            "currency_id": self.env.ref("base.BRL").id,
            "partner_id": self.partner.id,
        })
        
        self.assertEqual(transaction.provider_code, "pagarme")
        self.assertEqual(transaction.amount, 100.00)
        self.assertEqual(transaction.currency_id.name, "BRL")

    def test_webhook_url_computation(self):
        """Test webhook URL computation."""
        self.provider._compute_pagarme_webhook_url()
        self.assertTrue(self.provider.pagarme_webhook_url.endswith("/payment/pagarme/webhook"))

    def test_installment_data_preparation(self):
        """Test order data preparation for installments."""
        tx_values = {
            "amount": 120.00,
            "reference": "TEST-002",
        }
        
        order_data = self.provider._prepare_pagarme_order_data(tx_values)
        
        self.assertEqual(order_data["amount"], 12000)  # In cents
        self.assertEqual(order_data["currency"], "BRL")
        self.assertTrue(len(order_data["items"]) > 0)