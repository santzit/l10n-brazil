# Payment Pagar.me

This module provides Pagar.me payment gateway integration for Odoo 16.0 with transparent checkout functionality, specifically designed for the Brazilian market.

## Features

- **Transparent Checkout**: Process payments without redirecting customers to external pages
- **Brazilian Localization**: Full support for CPF/CNPJ, Brazilian addresses, and BRL currency
- **Credit Card Processing**: Support for major credit card brands (Visa, Mastercard, Elo, American Express)
- **Installment Payments**: Support for installment payments (parcelamento) up to 12x
- **Webhook Integration**: Automatic transaction status updates via webhooks
- **API Field Mapping**: Complete mapping between Odoo and Pagar.me API v5 fields following WooCommerce plugin patterns
- **Document Validation**: Real-time CPF/CNPJ validation
- **Address Lookup**: CEP-based address completion (ready for integration)
- **Card Brand Detection**: Automatic detection of card brands during input

## Installation

1. Install the module dependencies:
   ```bash
   pip install requests
   ```

2. Install the module in Odoo:
   - Place the module in your addons directory
   - Update the app list
   - Install the "Payment Pagar.me" module

## Configuration

1. Go to **Invoicing > Configuration > Payment Providers**
2. Create or edit the Pagar.me provider
3. Configure the following settings:
   - **API Key**: Your Pagar.me API key
   - **Encryption Key**: Your Pagar.me encryption key for card data
   - **State**: Set to "Enabled" for production or "Test" for testing
4. Configure the webhook URL in your Pagar.me dashboard:
   - Use webhook URL: `https://yourdomain.com/payment/pagarme/webhook`
   - This enables automatic transaction status updates

## Usage

### For Customers
- During checkout, select Pagar.me as payment method
- Enter credit card information directly on your website
- Fill in Brazilian-specific information (CPF/CNPJ, address)
- Choose number of installments
- Payment is processed transparently without redirection

### For Administrators
- View transaction details in payment transactions
- Monitor payment status updates via webhooks
- Access Pagar.me transaction IDs for reconciliation
- Track installment payments and card details

## Technical Details

### API Mapping

The module maps Odoo fields to Pagar.me API v5 fields following the WooCommerce pagarme-payments-for-woocommerce plugin (v3.6.0) patterns:

**Customer Data:**
- `partner.name` → `customer.name`
- `partner.email` → `customer.email`
- `partner.cnpj_cpf` → `customer.document`
- `partner.phone` → `customer.phones.home_phone`
- Brazilian address fields → `customer.address`

**Transaction Data:**
- `transaction.amount` → `amount` (in cents)
- Sale order lines → `items[]`
- Transaction reference → `metadata.odoo_reference`

**Payment Data:**
- Encrypted card information → `payment.credit_card.card`
- Installments → `payment.credit_card.installments`
- Payment method → `payment.payment_method`

### Webhooks

The module handles the following webhook events at `/payment/pagarme/webhook`:
- `transaction.paid` - Payment authorization and capture
- `transaction.refused` - Payment refusal
- `transaction.refunded` - Payment refund
- `transaction.chargeback` - Chargeback notifications
- `transaction.pending_refund` - Pending refund status

### Transaction Status Mapping

Pagar.me statuses are mapped to Odoo transaction states as follows:
- `paid` → `done`
- `pending` → `pending`
- `processing` → `pending`
- `failed` → `cancel`
- `canceled` → `cancel`
- `not_authorized` → `cancel`
- `refunded` → `cancel`
- `partial_refunded` → `done` (with refund tracking)

### Security Features

- **Data Encryption**: Card data is encrypted using Pagar.me's encryption key before transmission
- **API Security**: API keys are stored securely with restricted access
- **Webhook Validation**: Webhook data is validated before processing
- **Document Validation**: Real-time CPF/CNPJ validation using Brazilian algorithms
- **SSL Security**: All communications use HTTPS encryption

### Frontend Features

The transparent checkout form includes:
- **Input Masking**: Automatic formatting for card numbers, documents, phones, and CEP
- **Card Brand Detection**: Visual indication of detected card brand
- **Real-time Validation**: Immediate feedback on field validation
- **Installment Calculator**: Dynamic loading of available installment options
- **Address Lookup**: CEP-based address completion (extensible)
- **Responsive Design**: Mobile-friendly checkout experience

## File Structure

```
payment_pagarme/
├── __init__.py
├── __manifest__.py
├── README.md
├── controllers/
│   ├── __init__.py
│   └── main.py                 # Webhook and payment processing controllers
├── models/
│   ├── __init__.py
│   └── payment_transaction.py  # Transaction model with Pagar.me integration
├── data/
│   └── pagarme_provider.xml   # Payment provider configuration
├── views/
│   └── payment_pagarme_templates.xml  # Checkout templates
└── static/src/js/
    └── pagarme_checkout.js    # Frontend JavaScript for transparent checkout
```

## API Endpoints

The module provides the following HTTP endpoints:

- `POST /payment/pagarme/webhook` - Webhook handler for Pagar.me notifications
- `POST /payment/pagarme/process_payment` - Process transparent checkout payments
- `POST /payment/pagarme/get_installments` - Get available installment options
- `POST /payment/pagarme/validate_document` - Validate CPF/CNPJ documents
- `GET/POST /payment/pagarme/return` - Handle return from Pagar.me (fallback)

## Requirements

- **Odoo**: 16.0
- **Python packages**: requests
- **Pagar.me account**: Valid API credentials
- **Brazilian setup**: Proper CPF/CNPJ configuration in partner records
- **SSL certificate**: Required for production webhook handling

## Brazilian Market Compliance

This module is specifically designed for the Brazilian market and includes:
- CPF/CNPJ document validation
- Brazilian address format support
- BRL currency handling
- Installment payment support (common in Brazil)

## Integration with WooCommerce Plugin

The field mapping and API structure follows the patterns established in the WooCommerce pagarme-payments-for-woocommerce plugin version 3.6.0, ensuring compatibility and familiar behavior for merchants migrating from WooCommerce to Odoo.

## Troubleshooting

### Common Issues

1. **Webhook not receiving**: Ensure the webhook URL is correctly configured in Pagar.me dashboard
2. **SSL errors**: Verify SSL certificate is valid for webhook endpoints
3. **Document validation fails**: Check that CPF/CNPJ is properly formatted
4. **Payment not processing**: Verify API keys are correct and account is active

### Debug Mode

Enable debug mode by setting log level to INFO for `payment_pagarme` logger to see detailed webhook and API communication logs.

## Support

This module is designed specifically for Brazilian businesses using Pagar.me payment services. For technical support or feature requests, please contact the development team.

## License

AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

## Icon and Branding

The module includes Pagar.me branding elements:

- **Module Icon**: `static/description/icon.png` (128x128 PNG) - Used in Odoo app list
- **Payment Form Icon**: `static/src/img/pagarme-icon.png` (64x64 PNG) - Displayed in payment form
- **SVG Version**: `static/src/img/pagarme-icon.svg` - Scalable vector version

The icons feature a teal background (#20B2AA) with a white "P" letter, representing the Pagar.me brand colors. These can be replaced with official Pagar.me branded icons when available.

## Credits

- **Developer**: KMEE INFORMATICA LTDA
- **Community**: Odoo Community Association (OCA)
- **Based on**: WooCommerce pagarme-payments-for-woocommerce plugin v3.6.0 field mapping