# Mercado Pago Checkout Prefill Extension

This module extends the Odoo Mercado Pago integration to automatically send the user's name and VAT/CPF to Mercado Pago, allowing these fields to be prefilled on the Mercado Pago credit card checkout page.

## Features

- Prefills user name and VAT/CPF for credit card payments.
- Works for both individual (CPF) and company (CNPJ) identifications.

## Technical Details

Overrides the Mercado Pago payment preference creation to add `payer.name` and `payer.identification` fields based on the Odoo partner data.
