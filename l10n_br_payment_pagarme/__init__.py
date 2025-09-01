# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

from odoo import SUPERUSER_ID, api
from odoo.addons.payment import setup_provider, reset_payment_provider


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    setup_provider(env, 'pagarme')


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    reset_payment_provider(env, 'pagarme')