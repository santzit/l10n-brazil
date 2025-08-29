# Development Setup for GitHub Copilot

This guide explains how to set up your development environment to work with both the l10n-brazil localization modules and the Odoo core codebase.

## Prerequisites

- GitHub Copilot extension enabled in your IDE
- Git access to both repositories
- Python 3.8+ environment

## Repository Setup

To get full context for GitHub Copilot, clone both repositories:

### 1. Clone the l10n-brazil repository (this repo)
```bash
git clone https://github.com/OCA/l10n-brazil.git
cd l10n-brazil
git checkout 16.0
```

### 2. Clone the Odoo core repository (parallel directory)
```bash
cd ..
git clone https://github.com/odoo/odoo.git --branch 16.0 --depth 1
```

Your directory structure should look like:
```
workspace/
├── l10n-brazil/          # Brazilian localization modules
└── odoo/                 # Odoo core framework
    ├── addons/           # Standard addons
    └── odoo/
        └── addons/       # Base addons
```

## Copilot Configuration

The repository includes:

- `.github/copilot-instructions.md` - Instructions for GitHub Copilot
- `.github/mcp-server-config.json` - MCP server configuration
- `.vscode/settings.json` - VS Code workspace settings

These files ensure that GitHub Copilot has access to both repositories and understands the context of Odoo development.

## Verifying Setup

Once set up, GitHub Copilot should be able to:

1. **Find Odoo core modules** like `payment_demo`, `account`, `sale`, etc.
2. **Understand inheritance patterns** between l10n-brazil and core modules
3. **Provide context-aware suggestions** that respect both Brazilian requirements and Odoo standards
4. **Reference APIs and methods** from both repositories

## Testing Copilot Access

You can test if Copilot has proper access by:

1. Opening a Python file in a Brazilian module
2. Starting to type a reference to an Odoo core module (e.g., `from odoo.addons.payment...`)
3. Copilot should provide autocompletion based on the core repository

## Troubleshooting

If Copilot cannot find Odoo core modules:

1. Verify both repositories are cloned as described above
2. Ensure your IDE workspace includes both directories
3. Check that the `.vscode/settings.json` paths are correct
4. Restart your IDE to reload the configuration

## Module Dependencies

Common Odoo core modules used by l10n-brazil:

- `account` - Accounting framework
- `payment` - Payment processing (includes payment_demo)
- `sale` - Sales management
- `purchase` - Purchase management  
- `stock` - Inventory management
- `base` - Core framework
- `web` - Web interface
- `mail` - Messaging system

All of these should be accessible to Copilot after proper setup.