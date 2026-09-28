# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Optional traceability link for vendor bills: a Supplier or Packing House
    # bill can be tagged with the Supply Order it relates to.
    #
    # Defined here rather than in hitac_base (which owns the rest of the Hitac
    # traceability group) because the comodel is this module's. hitac_base must
    # not depend on hitac_supply — hitac_supply's ACLs reference hitac_base's
    # security groups, so the reverse dependency would be a cycle.
    hitac_supply_order_id = fields.Many2one('supply.order', string='Supply Order')
