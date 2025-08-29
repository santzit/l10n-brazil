# Pagar.me Payment Provider

Simple Payment Provider for Pagar.me following Stripe module patterns.

## Configuration

1. Go to **Invoicing > Configuration > Payment Acquirers**
2. Select **Pagar.me** 
3. Enter your **App ID** and **API Key** from Pagar.me dashboard
4. Set the provider to **Enabled**

## Features

- Credit card payments via Pagar.me REST API
- Simple integration following Odoo payment provider standards
- Brazilian market support

## Technical Structure

Based on Stripe module patterns:

- `payment.acquirer` with `_get_pagarme_webhook_url()` method
- `payment.transaction` with `_send_payment_request()` and `_get_specific_processing_values()` methods

## Requirements

- `requests` Python library
- Pagar.me account with API credentials