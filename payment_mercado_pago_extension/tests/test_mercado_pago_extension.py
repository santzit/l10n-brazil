from odoo.tests.common import TransactionCase

class TestMercadoPagoExtension(TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'test@example.com',
            'vat': '12345678901',  # CPF format
        })
        
        # Create a Mercado Pago acquirer
        self.acquirer = self.env['payment.acquirer'].create({
            'name': 'Mercado Pago Test',
            'provider': 'mercado_pago',
            'state': 'test',
            'mercado_pago_public_key': 'TEST-test-public-key-12345',
        })
    
    def test_payment_acquirer_fields(self):
        """Test that the Mercado Pago public key field exists and works"""
        self.assertTrue(hasattr(self.acquirer, 'mercado_pago_public_key'))
        self.assertEqual(self.acquirer.mercado_pago_public_key, 'TEST-test-public-key-12345')
    
    def test_prepare_payment_values_cpf(self):
        """Test payment values preparation with CPF"""
        values = self.acquirer._mercado_pago_prepare_payment_values(self.partner)
        self.assertIn('payer', values)
        self.assertEqual(values['payer']['name'], 'Test Customer')
        self.assertEqual(values['payer']['identification']['type'], 'CPF')
        self.assertEqual(values['payer']['identification']['number'], '12345678901')
    
    def test_prepare_payment_values_cnpj(self):
        """Test payment values preparation with CNPJ"""
        self.partner.vat = '12345678901234'  # CNPJ format
        values = self.acquirer._mercado_pago_prepare_payment_values(self.partner)
        self.assertEqual(values['payer']['identification']['type'], 'CNPJ')
        self.assertEqual(values['payer']['identification']['number'], '12345678901234')
    
    def test_prepare_payment_values_no_vat(self):
        """Test payment values preparation without VAT"""
        self.partner.vat = False
        values = self.acquirer._mercado_pago_prepare_payment_values(self.partner)
        self.assertEqual(values['payer']['name'], 'Test Customer')
        self.assertNotIn('identification', values['payer'])
    
    def test_payment_transaction_charge(self):
        """Test payment transaction charge simulation"""
        transaction = self.env['payment.transaction'].create({
            'acquirer_id': self.acquirer.id,
            'partner_id': self.partner.id,
            'amount': 100.0,
            'currency_id': self.env.ref('base.BRL').id,
            'reference': 'TEST-TX-001',
        })
        
        result = transaction.mercado_pago_api_charge({'test': 'data'})
        self.assertEqual(result['status'], 'success')
        self.assertIn('message', result)
        self.assertEqual(result['transaction_id'], transaction.id)
        self.assertEqual(result['provider_public_key'], 'TEST-test-public-key-12345')