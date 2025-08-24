# Stone/Pagar.me Payment Provider

This module provides Stone/Pagar.me payment gateway integration for Odoo 16.0 with transparent checkout functionality, specifically designed for the Brazilian market.

## Features

- **Transparent Checkout**: Process payments without redirecting customers to external pages
- **Brazilian Localization**: Full support for CPF/CNPJ, Brazilian addresses, and BRL currency
- **Credit Card Processing**: Support for major credit card brands
- **Installment Payments**: Support for installment payments (parcelamento)
- **Webhook Integration**: Automatic transaction status updates via webhooks
- **API Field Mapping**: Complete mapping between Odoo and Pagar.me API fields

## Installation

1. Install the module dependencies:
   ```bash
   pip install requests
   ```

2. Install the module in Odoo:
   - Place the module in your addons directory
   - Update the app list
   - Install the "Stone/Pagar.me Payment Provider" module

## Configuration

1. Go to **Invoicing > Configuration > Payment Providers**
2. Create or edit the Stone/Pagar.me provider
3. Configure the following settings:
   - **API Key**: Your Stone/Pagar.me API key
   - **Encryption Key**: Your Stone/Pagar.me encryption key for card data
   - **State**: Set to "Enabled" for production or "Test" for testing
4. Configure the webhook URL in your Stone/Pagar.me dashboard:
   - Use the webhook URL shown in the provider configuration
   - This enables automatic transaction status updates

## Usage

### For Customers
- During checkout, select Stone/Pagar.me as payment method
- Enter credit card information directly on your website
- Choose number of installments
- Payment is processed transparently without redirection

### For Administrators
- View transaction details in payment transactions
- Monitor payment status updates via webhooks
- Access Stone/Pagar.me transaction IDs for reconciliation

## Technical Details

### API Mapping
The module maps Odoo fields to Pagar.me API fields as follows:

**Customer Data:**
- `partner.name` → `customer.name`
- `partner.email` → `customer.email`
- `partner.cnpj_cpf` → `customer.document`
- `partner.phone` → `customer.phones.home_phone`
- Address fields → `customer.address`

**Order Data:**
- `transaction.amount` → `order.amount` (in cents)
- Sale order lines → `order.items`
- Transaction reference → `metadata.odoo_reference`

**Payment Data:**
- Card information (encrypted) → `payment.credit_card`
- Installments → `payment.credit_card.installments`

### Webhooks
The module handles the following webhook events:
- Payment authorization
- Payment capture
- Payment cancellation
- Chargeback notifications

### Security
- API keys are stored securely with restricted access
- Card data is encrypted using Pagar.me's encryption key
- Webhook data is validated before processing

## Requirements

- Odoo 16.0
- Python requests library
- Valid Stone/Pagar.me account with API credentials
- Brazilian company setup (for proper CPF/CNPJ handling)

## Support

This module is designed specifically for Brazilian businesses using Stone/Pagar.me payment services. For technical support or feature requests, please contact the development team.

## License

AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)