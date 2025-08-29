# Brazilian Payment Provider: Pagar.me

This module provides a secure payment provider integration for [Pagar.me](https://pagar.me) in Odoo 16, specifically designed for the Brazilian market.

## Features

- **Secure Tokenization**: Card data is tokenized in the frontend and never touches the Odoo backend
- **PCI Compliance**: Follows security best practices from WooCommerce Pagar.me plugin and Odoo Stripe module
- **Brazilian Market Focus**: Supports BRL currency and Brazilian card brands (Visa, Mastercard, Amex, Diners, Elo)
- **Real-time Updates**: Webhook integration for payment status updates
- **Admin Configuration**: Easy setup through Odoo admin interface

## Security Architecture

The module follows a secure architecture where:

1. **Frontend Tokenization**: Card data is collected via JavaScript and sent directly to Pagar.me API for tokenization
2. **Token-only Backend**: Only the generated token is submitted to Odoo's backend
3. **No Card Storage**: Raw card data never reaches or is stored on Odoo servers
4. **Webhook Validation**: Secure webhook signature validation for status updates

## Installation

1. Install the module through Odoo Apps or by copying to your addons directory
2. Update the app list and install "Brazilian Payment Provider: Pagar.me"

## Configuration

### 1. Pagar.me Dashboard Setup

1. Access your [Pagar.me Dashboard](https://dashboard.pagar.me)
2. Go to "Configurações" > "Chaves de API"
3. Copy your API keys (use test keys for development)

### 2. Odoo Configuration

1. Go to **Invoicing > Configuration > Payment Acquirers**
2. Find and edit the "Pagar.me" record
3. Set the state to "Test" or "Enabled"
4. Fill in the required fields:
   - **API Key**: Your Pagar.me secret key (sk_test_xxx or sk_live_xxx)
   - **Encryption Key**: Your Pagar.me encryption key (ek_test_xxx or ek_live_xxx)
   - **Webhook Secret**: Optional webhook secret for signature validation

### 3. Webhook Setup

Configure the following webhook URL in your Pagar.me dashboard:
```
https://yourdomain.com/payment/pagarme/webhook
```

## Usage

Once configured, Pagar.me will appear as a payment option during checkout. Customers can enter their card details securely, and payments will be processed through Pagar.me's platform.

## Supported Cards

- Visa
- Mastercard
- American Express
- Diners Club
- Elo

## API Reference

The module integrates with Pagar.me's REST API v5:
- **Tokenization**: `POST /core/v5/tokens`
- **Charges**: `POST /core/v5/charges`
- **Webhooks**: For real-time payment status updates

## Development

### Testing

Run tests with:
```bash
odoo-bin -d test_db -i l10n_br_payment_pagarme --test-tags=post_install
```

### Architecture

The module follows Odoo's payment provider architecture:

- `models/payment_acquirer.py`: Main acquirer configuration and API integration
- `models/payment_transaction.py`: Transaction handling and status management
- `controllers/main.py`: HTTP controllers for webhooks and returns
- `static/src/js/pagarme_form.js`: Frontend tokenization logic

## Security Considerations

- Always use HTTPS in production
- Use test API keys during development
- Keep API keys secure and never commit them to version control
- Regularly rotate API keys
- Validate webhook signatures to prevent fraud

## Support

For issues related to this module, please create an issue in the [OCA l10n-brazil repository](https://github.com/OCA/l10n-brazil).

For Pagar.me API issues, consult the [official documentation](https://docs.pagar.me/).

## License

This module is licensed under AGPL-3.0.

## Credits

This module was developed following best practices from:
- [WooCommerce Pagar.me Plugin](https://github.com/pagarme/woocommerce)
- [Odoo Stripe Payment Provider](https://github.com/odoo/odoo/tree/16.0/addons/payment_stripe)