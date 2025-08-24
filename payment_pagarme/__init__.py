
# Copyright 2025 SANTZ IT
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from . import models
from . import controllers
from odoo.addons.payment import setup_provider, reset_payment_provider


def post_init_hook(cr, registry):
    setup_provider(cr, registry, 'pagarme')


def uninstall_hook(cr, registry):
    reset_payment_provider(cr, registry, 'pagarme')