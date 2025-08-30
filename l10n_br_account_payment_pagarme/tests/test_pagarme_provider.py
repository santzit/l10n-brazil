# Copyright 2024 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..constants.pagarme_api import PAGARME_TRANSACTION_STATUS


@tagged("post_install", "-at_install")
class TestPagarmeProvider(TransactionCase):
    """Test Pagar.me payment provider functionality."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create Pagar.me payment provider
        cls.provider = cls.env["payment.provider"].create({
            "name": "Pagar.me Test",
            "code": "pagarme",
            "state": "test",
            "pagarme_api_key": "sk_test_123456789",
            "pagarme_public_key": "pk_test_123456789",
            "pagarme_sandbox_mode": True,
            "pagarme_enable_credit_card": True,
            "pagarme_enable_boleto": True,
            "pagarme_enable_pix": True,
        })

        # Create currency (BRL)
        cls.currency_brl = cls.env["res.currency"].search([("name", "=", "BRL")], limit=1)
        if not cls.currency_brl:
            cls.currency_brl = cls.env["res.currency"].create({
                "name": "BRL",
                "symbol": "R$",
                "decimal_places": 2,
            })

        # Create partner
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Customer",
            "email": "test@example.com",
            "cnpj_cpf": "12345678901",
            "is_company": False,
        })

    def test_provider_configuration(self):
        """Test provider configuration validation."""
        self.assertEqual(self.provider.code, "pagarme")
        self.assertTrue(self.provider.pagarme_sandbox_mode)
        self.assertTrue(self.provider.pagarme_enable_credit_card)

    def test_supported_currencies(self):
        """Test that only BRL is supported."""
        supported_currencies = self.provider._get_supported_currencies()
        brl_currencies = supported_currencies.filtered(lambda c: c.name == "BRL")
        self.assertTrue(brl_currencies, "BRL currency should be supported")

    @patch("requests.post")
    def test_pagarme_api_request(self, mock_post):
        """Test API request functionality."""
        # Mock successful API response
        mock_response = mock_post.return_value
        mock_response.json.return_value = {"id": "tran_123", "status": "paid"}
        mock_response.raise_for_status.return_value = None

        # Test API request
        response = self.provider._pagarme_make_request("transactions", {"test": "data"})
        
        self.assertEqual(response["id"], "tran_123")
        self.assertEqual(response["status"], "paid")

    def test_transaction_status_mapping(self):
        """Test transaction status mapping."""
        # Test status mapping
        self.assertEqual(PAGARME_TRANSACTION_STATUS["paid"], "done")
        self.assertEqual(PAGARME_TRANSACTION_STATUS["refused"], "canceled")
        self.assertEqual(PAGARME_TRANSACTION_STATUS["processing"], "pending")

    def test_webhook_url_computation(self):
        """Test webhook URL computation."""
        self.provider._compute_webhook_url()
        self.assertIn("/payment/pagarme/webhook", self.provider.pagarme_webhook_url)

    def test_installment_validation(self):
        """Test installment validation constraints."""
        # Test valid installments
        self.provider.pagarme_max_installments = 12
        self.provider._check_max_installments()  # Should not raise

        # Test invalid installments 
        with self.assertRaises(Exception):
            self.provider.pagarme_max_installments = 25
            self.provider._check_max_installments()

    def test_min_installment_amount_validation(self):
        """Test minimum installment amount validation."""
        # Test valid amount
        self.provider.pagarme_min_installment_amount = 5.00
        self.provider._check_min_installment_amount()  # Should not raise

        # Test invalid amount
        with self.assertRaises(Exception):
            self.provider.pagarme_min_installment_amount = 0.50
            self.provider._check_min_installment_amount()

    def test_payment_transaction_creation(self):
        """Test payment transaction creation."""
        # Create payment transaction
        transaction = self.env["payment.transaction"].create({
            "reference": "TEST-001",
            "amount": 100.00,
            "currency_id": self.currency_brl.id,
            "partner_id": self.partner.id,
            "provider_id": self.provider.id,
            "pagarme_payment_method": "credit_card",
            "pagarme_installments": 3,
        })

        self.assertEqual(transaction.provider_code, "pagarme")
        self.assertEqual(transaction.pagarme_payment_method, "credit_card")
        self.assertEqual(transaction.pagarme_installments, 3)

    def test_customer_data_preparation(self):
        """Test customer data preparation for API."""
        transaction = self.env["payment.transaction"].create({
            "reference": "TEST-002",
            "amount": 50.00,
            "currency_id": self.currency_brl.id,
            "partner_id": self.partner.id,
            "provider_id": self.provider.id,
            "pagarme_payment_method": "boleto",
        })

        customer_data = transaction._pagarme_prepare_customer_data()
        
        self.assertEqual(customer_data["name"], "Test Customer")
        self.assertEqual(customer_data["email"], "test@example.com")
        self.assertEqual(customer_data["type"], "individual")
        self.assertEqual(customer_data["document"], "12345678901")
        self.assertEqual(customer_data["document_type"], "cpf")

    def test_cnab_config_integration(self):
        """Test CNAB configuration integration."""
        # Create CNAB config
        cnab_config = self.env["l10n_br_cnab_config"].create({
            "name": "Test Pagar.me Config",
            "cnab_processor": "pagarme",
            "bank_id": self.env.ref("l10n_br_base.res_bank_341").id,
            "payment_method_id": self.env.ref("l10n_br_account_payment_order.payment_method_type_240").id,
            "pagarme_api_key": "sk_test_123456789",
            "pagarme_public_key": "pk_test_123456789",
            "pagarme_payment_method": "credit_card",
        })

        self.assertEqual(cnab_config.cnab_processor, "pagarme")
        self.assertTrue(cnab_config.pagarme_webhook_url)

    @patch("requests.get")  
    def test_connection_test(self, mock_get):
        """Test API connection test."""
        # Mock successful response
        mock_response = mock_get.return_value
        mock_response.json.return_value = {"available": {"amount": 100000}}
        mock_response.raise_for_status.return_value = None

        success, message = self.provider._pagarme_test_connection()
        
        self.assertTrue(success)
        self.assertIn("successful", message.lower())