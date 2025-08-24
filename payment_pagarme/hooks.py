# Copyright 2024 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """Post-installation hook to setup Pagar.me payment provider."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Find the Pagar.me payment provider
    provider = env.ref("payment_pagarme.payment_provider_pagarme", raise_if_not_found=False)
    
    if provider:
        _logger.info("Setting up Pagar.me payment provider...")
        
        # Ensure the provider is properly configured
        provider.write({
            'state': 'disabled',  # Keep disabled until merchant configures API keys
            'is_published': False,
            'capture_manually': False,
            'allow_tokenization': True,
        })
        
        _logger.info("Pagar.me payment provider setup completed.")
    else:
        _logger.warning("Pagar.me payment provider not found during post-installation.")


def uninstall_hook(cr, registry):
    """Uninstallation hook to reset Pagar.me payment provider."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Find the Pagar.me payment provider
    provider = env.ref("payment_pagarme.payment_provider_pagarme", raise_if_not_found=False)
    
    if provider:
        _logger.info("Resetting Pagar.me payment provider...")
        
        # Disable the provider and reset configuration
        provider.write({
            'state': 'disabled',
            'is_published': False,
            'pagarme_api_key': '',
            'pagarme_encryption_key': '',
        })
        
        _logger.info("Pagar.me payment provider reset completed.")
    else:
        _logger.warning("Pagar.me payment provider not found during uninstallation.")