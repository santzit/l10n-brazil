# Pagar.me Payment Provider

This module provides integration with Pagar.me payment gateway for Odoo 16, specifically designed for the Brazilian market.

## Features

- **Secure Frontend Tokenization**: Card data is tokenized in the browser and never touches your server
- **PCI Compliance**: Follows security best practices to ensure PCI compliance
- **Credit Card Payments**: Support for major credit cards through Pagar.me
- **Real-time Notifications**: Webhook support for instant payment status updates
- **Brazilian Optimization**: Designed specifically for Brazilian e-commerce requirements

## Security

This module follows security best practices inspired by:
- [WooCommerce Pagar.me Plugin](https://github.com/pagarme/woocommerce)
- [Odoo Stripe Module](https://github.com/odoo/odoo/tree/16.0/addons/payment_stripe)

Key security features:
- All card data is tokenized in the browser before submission
- Only tokens are processed on the backend
- No sensitive payment data is stored in Odoo
- Secure API communication with Pagar.me

## Installation

1. Install the module through Odoo Apps or copy to addons directory
2. Update module list and install "Pagar.me Payment Provider"
3. Configure your Pagar.me credentials in Payment Acquirers

## Configuration

1. Go to **Invoicing > Configuration > Payment Acquirers**
2. Find "Pagar.me" and open it
3. Enter your Pagar.me credentials:
   - **App ID**: Your Pagar.me public key (pk_test_... or pk_live_...)
   - **API Key**: Your Pagar.me private key (sk_test_... or sk_live_...)
4. Set the state to "Enabled" when ready for production
5. Use "Test Connection" to verify your credentials

## Usage

Once configured, Pagar.me will appear as a payment option during checkout. Customers can securely enter their card details, which are tokenized by Pagar.me before being processed.

## Technical Details

### Tokenization Flow

1. Customer enters card details in the browser
2. JavaScript tokenizes card data with Pagar.me API
3. Only the token is sent to Odoo backend
4. Backend creates order using the token
5. Payment status is updated via webhooks

### API Integration

- **Tokenization**: `POST https://api.pagar.me/core/v5/tokens`
- **Orders**: `POST https://api.pagar.me/core/v5/orders`
- **Webhooks**: Automatic status updates

## Development

This module follows Odoo development best practices and includes:
- Comprehensive tests
- Proper security controls
- Clean separation of concerns
- Extensive documentation

## Support

For issues and support, please visit the [GitHub repository](https://github.com/OCA/l10n-brazil).

## License

AGPL-3.0 or later