# Odoo Brazilian Localization (l10n-brazil)

**Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

The l10n-brazil repository contains 53 Odoo addons providing comprehensive Brazilian fiscal localization including electronic invoicing (NF-e, NFS-e, CT-e), tax calculations, and regulatory compliance. This is a complex project with 848 Python files and 430 XML files requiring specialized Brazilian fiscal libraries.

## Required Repository Access

To provide comprehensive assistance, the GitHub Copilot agent should have access to:

- **Primary Repository**: `OCA/l10n-brazil` (current repository) - Contains Brazilian-specific modules
- **Odoo Core Repository**: `https://github.com/odoo/odoo` (branch: `16.0`) - Contains base Odoo framework and standard modules

The modules in this repository depend on standard Odoo modules such as `account`, `sale`, `purchase`, `stock`, `payment` (including `payment_demo`), `base`, and many others from the Odoo core.

## Required Repository Access

To provide comprehensive assistance, the GitHub Copilot agent should have access to:

- **Primary Repository**: `OCA/l10n-brazil` (current repository) - Contains Brazilian-specific modules
- **Odoo Core Repository**: `https://github.com/odoo/odoo` (branch: `16.0`) - Contains base Odoo framework and standard modules

The modules in this repository depend on standard Odoo modules such as `account`, `sale`, `purchase`, `stock`, `payment` (including `payment_demo`), `base`, and many others from the Odoo core.


## Working Effectively

### Environment Setup
- Install Python dependencies: `pip3 install -r requirements.txt` - takes 2-3 minutes. NEVER CANCEL.
- Install test dependencies: `pip3 install -r test-requirements.txt` - may fail due to network timeouts. Document failures.
- Install development tools: `pip3 install pre-commit ruff` - takes 1-2 minutes.

### Code Quality and Linting 
- **CRITICAL**: Always run `ruff check .` before committing - takes 0.1 seconds, extremely fast.
- Format code: `ruff format .` - takes 0.1 seconds.
- Install pre-commit hooks: `pre-commit install` - setup takes 5-10 minutes due to network dependencies. NEVER CANCEL.
- Run pre-commit: `pre-commit run --all-files` - takes 10-15 minutes for full validation. NEVER CANCEL.
- Syntax check individual modules: `python3 -m py_compile $(find l10n_br_base/ -name "*.py")` - takes 0.05 seconds per module.

### Testing and Validation
- **IMPORTANT**: This project uses OCA testing infrastructure requiring specialized Docker containers.
- Local testing requires Odoo environment setup - modules cannot be imported without Odoo.
- Full CI testing runs in container: `ghcr.io/oca/oca-ci/py3.10-odoo16.0:latest`
- OCA commands (require container): `oca_install_addons`, `oca_init_test_database`, `oca_run_tests`
- **NEVER try to run OCA commands outside Docker containers** - they will fail.

### Development Workflow
- Edit files → `ruff check .` → `ruff format .` → commit
- For comprehensive testing: use CI or setup full OCA development environment
- Test functionality: Use [Runboat demo environment](https://runboat.odoo-community.org/builds?repo=OCA/l10n-brazil&target_branch=16.0)

## Validation

### Manual Testing Requirements
- **ALWAYS** run `ruff check .` and `ruff format .` after any code changes
- **ALWAYS** test syntax: `python3 -m py_compile path/to/changed/file.py`
- **CANNOT** run functional tests locally without full Odoo setup
- **USE** Runboat for functional validation: Click "Try me" button in README for live demo

### Code Quality Standards
- All code must pass ruff linting (0 errors policy)
- XML files must be valid: test with `python3 -c "import xml.etree.ElementTree as ET; ET.parse('file.xml')"`
- Pre-commit hooks enforce: ruff, pylint-odoo, prettier, eslint
- **WARNING**: Pre-commit first run takes 10+ minutes for environment setup

## Common Tasks

### Key Modules and Their Purpose
```bash
# Core modules
l10n_br_base/          # Brazilian localization foundation
l10n_br_fiscal/        # Fiscal/tax engine for Brazil
l10n_br_nfe/          # Electronic invoicing (NF-e)
l10n_br_account/      # Brazilian accounting
spec_driven_model/    # XML binding framework

# Module count: 53 modules total
find . -name "__manifest__.py" | wc -l  # Returns: 53
```

### Repository Structure Overview
```bash
# Repository stats
find . -name "*.py" | wc -l    # 848 Python files  
find . -name "*.xml" | wc -l   # 430 XML files
ls l10n_br_*/                 # Lists all 52 Brazilian modules
ls spec_driven_model/         # Special XML binding framework
```

### Dependencies and External Libraries
```bash
# Brazilian fiscal libraries (specialized)
erpbrasil.assinatura>=1.7.0  # Digital signatures
erpbrasil.base>=2.3.0        # Base Brazilian utilities  
erpbrasil.edoc>=2.5.2        # Electronic documents
nfelib<=2.0.7                # NFe library
```

### Common Errors and Solutions
- **Import failures**: Normal without Odoo environment, use Runboat for testing
- **Pre-commit network timeouts**: Use `--no-verify` flag for commits during network issues
- **OCA command failures**: These require Docker containers, use CI for validation
- **Ruff configuration warnings**: Update `.ruff.toml` to move settings to `[lint]` section

### Timing Expectations
- Dependency installation: 2-3 minutes - NEVER CANCEL
- Ruff full repository check: 0.1 seconds
- Ruff format check: 0.1 seconds  
- Pre-commit environment setup: 10+ minutes first time - NEVER CANCEL
- Pre-commit full validation: 10-15 minutes - NEVER CANCEL
- Python syntax check per module: 0.05 seconds

### Critical Warnings
- **NEVER CANCEL** dependency installations or pre-commit setups
- **ALWAYS** use Runboat for functional testing if you cannot setup full Odoo environment
- **DO NOT** attempt to run modules standalone - they require Odoo framework
- **NETWORK TIMEOUTS** are common for Brazilian fiscal libraries - retry with longer timeouts

## Development Notes

### Brazilian Fiscal Complexity
This localization handles complex Brazilian tax regulations including:
- Multiple tax types (ICMS, IPI, ISS, PIS, COFINS)
- Electronic fiscal documents (NF-e, NFS-e, CT-e, MDF-e)
- SPED compliance and reporting
- Bank integration (CNAB 240/400)
- State and municipal tax variations

### Module Dependencies
Most modules depend on `l10n_br_base` and `l10n_br_fiscal`. Check `__manifest__.py` files for specific dependencies before making changes.

Brazilian modules typically extend core Odoo functionality and follow the naming convention `l10n_br_*`. They integrate with Brazilian fiscal, tax, and legal requirements while inheriting from standard Odoo models and APIs.

### Testing Strategy
1. **Code quality**: Use ruff locally (very fast)
2. **Syntax validation**: Use Python compilation (fast)
3. **Functional testing**: Use Runboat demo or full CI pipeline
4. **Integration testing**: Requires OCA Docker environment
