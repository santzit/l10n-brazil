# Payment Provider: Pagar.me

## Overview

This module provides a Pagar.me payment provider integration for the Brazilian localization of Odoo. It extends the standard Odoo payment framework to support Pagar.me as a payment provider.

## Features

- **Payment Provider Integration**: Adds Pagar.me as a selectable payment provider
- **Simulated Payments**: Supports test/simulation mode for development and testing
- **Express Checkout**: Includes express checkout functionality
- **Token Support**: Supports payment tokenization for recurring payments
- **Partial Refunds**: Supports partial refund operations
- **Manual Capture**: Supports manual payment capture

## Installation

1. Copy this module to your Odoo addons directory
2. Update the addons list in Odoo
3. Install the module from the Apps menu

## Configuration

1. Go to **Invoicing > Configuration > Payment Providers**
2. Select or create a Pagar.me provider
3. Configure the provider settings as needed
4. Set the provider to "Test" mode for development

## Usage

The module provides the same functionality as the demo payment provider but branded for Pagar.me. This is intended as a foundation for implementing actual Pagar.me API integration.

## Development Notes

This module is currently implemented as a simulation/demo provider. For production use, you would need to:

1. Integrate with the actual Pagar.me API
2. Implement real payment processing logic
3. Add proper security and error handling
4. Configure production credentials

## Technical Details

- **Provider Code**: `pagarme`
- **Payment Method Code**: `pagarme`
- **Supported Features**: Tokenization, Express Checkout, Partial Refunds, Manual Capture
- **Test Routes**: `/payment/pagarme/simulate_payment`

## Files Structure

```
l10n_br_payment_pagarme/
├── __init__.py
├── __manifest__.py
├── const.py
├── controllers/
│   ├── __init__.py
│   └── main.py
├── data/
│   ├── payment_method_data.xml
│   └── payment_provider_data.xml
├── models/
│   ├── __init__.py
│   ├── payment_provider.py
│   ├── payment_token.py
│   └── payment_transaction.py
├── static/
│   ├── img/
│   │   └── pagarme.png
│   └── src/
│       └── js/
│           ├── express_checkout_form.js
│           ├── payment_form.js
│           └── payment_pagarme_mixin.js
├── tests/
│   ├── __init__.py
│   └── test_pagarme.py
└── views/
    ├── payment_pagarme_templates.xml
    ├── payment_provider_views.xml
    ├── payment_token_views.xml
    └── payment_transaction_views.xml
```

## License

LGPL-3

## Authors

Created as part of the l10n-brazil project for Odoo Brazilian localization.