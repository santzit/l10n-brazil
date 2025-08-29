# GitHub Copilot Instructions for l10n-brazil

## Context

This repository contains Brazilian localization modules for Odoo 16.0. When working with this codebase, you should have access to both:

1. **OCA/l10n-brazil repository** (this repository) - Contains Brazilian-specific modules
2. **Odoo core codebase** (version 16.0) - Contains base Odoo framework and standard modules

## Required Repository Access

To provide comprehensive assistance, the GitHub Copilot agent should have access to:

- **Primary Repository**: `OCA/l10n-brazil` (current repository)
- **Odoo Core Repository**: `https://github.com/odoo/odoo` (branch: `16.0`)

## Module Dependencies

The modules in this repository depend on standard Odoo modules such as:
- `account` - Accounting framework
- `sale` - Sales management  
- `purchase` - Purchase management
- `stock` - Inventory management
- `payment` - Payment processing (including `payment_demo`)
- `base` - Core Odoo framework
- Many others from the Odoo core

## Development Context

When providing code suggestions or analyzing issues:

1. **Check both repositories** for existing implementations
2. **Understand Odoo inheritance patterns** from core modules
3. **Follow Brazilian localization conventions** established in this repository
4. **Reference standard Odoo APIs** available in the core codebase

## Common Patterns

- Brazilian modules typically extend core Odoo functionality
- They follow the naming convention `l10n_br_*`
- They often depend on `l10n_br_base` and other Brazilian modules
- They integrate with Brazilian fiscal, tax, and legal requirements

This setup ensures comprehensive understanding of both the localization modules and the underlying Odoo framework.