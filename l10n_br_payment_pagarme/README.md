# Brazilian Pagar.me Payment Provider

Payment Provider for Pagar.me following Stripe module patterns, designed for Brazilian e-commerce.

## Configuration

1. Go to **Invoicing > Configuration > Payment Providers**
2. Select **Pagar.me** 
3. Enter your **App ID** and **API Key** from Pagar.me dashboard
4. Set the provider to **Enabled**

## Features

- Credit card payments via Pagar.me REST API with Tokenize.js
- Simple integration following Odoo payment provider standards
- Brazilian market support
- Secure credit card tokenization

## Technical Structure

Based on Stripe module patterns:

- `payment.provider` with `_get_pagarme_webhook_url()` method
- `payment.transaction` with `_send_payment_request()` and `_get_specific_processing_values()` methods
- JavaScript credit card form with Tokenize.js integration
- Post-install and uninstall hooks for provider setup

## Requirements

- `requests` Python library
- Pagar.me account with API credentials
- Modern web browser with JavaScript enabled