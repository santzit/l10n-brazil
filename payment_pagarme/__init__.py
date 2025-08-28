
# Copyright 2025 SANTZ IT
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from . import models
from . import controllers


def post_init_hook(cr, registry):
    """Post-installation setup for Pagar.me payment provider."""
    from odoo.api import Environment
    
    env = Environment(cr, 1, {})  # Admin user
    
    # Find the Pagar.me provider
    provider = env['payment.provider'].search([('code', '=', 'pagarme')], limit=1)
    if provider:
        # Ensure provider is properly configured
        provider.write({
            'state': 'disabled',  # Start disabled until user configures
            'support_express_checkout': True,
            'allow_tokenization': False,
            'support_tokenization': False,
        })


def uninstall_hook(cr, registry):
    """Cleanup when uninstalling Pagar.me payment provider."""
    from odoo.api import Environment
    
    env = Environment(cr, 1, {})  # Admin user
    
    # Find and disable the provider
    provider = env['payment.provider'].search([('code', '=', 'pagarme')], limit=1)
    if provider:
        # Disable the provider and clean up any related data
        provider.write({'state': 'disabled'})