# Quick Reference: GitHub Copilot with Odoo

## Repository Structure for Copilot

```
workspace/
├── l10n-brazil/              # Brazilian localization (this repo)
│   ├── l10n_br_account/      # Brazilian accounting
│   ├── l10n_br_fiscal/       # Brazilian fiscal framework  
│   ├── l10n_br_payment_*/    # Brazilian payment modules
│   └── ...
└── odoo/                     # Odoo core (clone separately)
    ├── addons/
    │   ├── account/          # Core accounting
    │   ├── payment/          # Core payment (includes payment_demo)
    │   ├── sale/             # Sales management
    │   ├── purchase/         # Purchase management
    │   └── ...
    └── odoo/addons/
        ├── base/             # Core framework
        ├── web/              # Web interface
        └── ...
```

## Copilot Context Files

| File | Purpose |
|------|---------|
| `.github/copilot-instructions.md` | Main instructions for Copilot |
| `.github/mcp-server-config.json` | MCP server configuration |
| `.vscode/settings.json` | VS Code workspace settings |
| `l10n-brazil-odoo.code-workspace` | Multi-folder workspace |
| `docs/copilot-setup.md` | Detailed setup guide |

## Key Commands to Test Copilot Setup

1. **Test Odoo core module access:**
   ```python
   from odoo.addons.payment.models.payment_provider import PaymentProvider
   ```

2. **Test Brazilian module access:**
   ```python
   from odoo.addons.l10n_br_base.models.res_partner import ResPartner
   ```

3. **Test inheritance patterns:**
   ```python
   class PaymentProvider(models.Model):
       _inherit = 'payment.provider'
       # Copilot should suggest Brazilian-specific fields
   ```

## Expected Copilot Behavior

- ✅ Finds `payment_demo` and other core modules
- ✅ Understands Odoo inheritance patterns
- ✅ Suggests Brazilian-specific implementations
- ✅ References both repositories for context
- ✅ Provides accurate API suggestions

## Troubleshooting

If Copilot cannot find core modules:
1. Ensure `../odoo` directory exists with Odoo 16.0
2. Open the workspace file: `l10n-brazil-odoo.code-workspace`
3. Restart VS Code
4. Check that both folders appear in the workspace