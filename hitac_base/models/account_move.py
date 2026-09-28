# -*- coding: utf-8 -*-
import base64

from odoo import api, fields, models
from odoo.tools import file_open

# Which Hitac Invoicing > Expenses menu a vendor document belongs to (see
# views/invoicing_menus.xml). Independent of partner_id.hitac_type / product
# hitac_type — those only seed a default/backfill; this field is the actual
# source of truth used to route records into the right menu, so a record can
# be reclassified without needing to change its vendor or lines.
HITAC_EXPENSE_TYPES = [
    ('supplier', 'Supplier'),
    ('packing_house', 'Packing House'),
    ('packaging', 'Packagings and Equipment'),
    ('employee', 'Employee'),
    ('other', 'Expenses'),
]


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Optional traceability link for vendor bills — a Packing House bill can be
    # tagged with the Sales Order it relates to (see views/invoicing_menus.xml
    # for the Expenses menu structure this supports).
    #
    # The matching Supply Order link lives in hitac_supply, not here: pointing at
    # supply.order from this module would force hitac_base to depend on
    # hitac_supply, while hitac_supply's ACLs need hitac_base's groups — a cycle
    # that broke clean installs.
    hitac_sale_order_id = fields.Many2one('sale.order', string='Sales Order')

    hitac_expense_type = fields.Selection(HITAC_EXPENSE_TYPES, string='Expense Type')

    # Non-stored: whether the current user may see the "Payments" stat
    # button. Once a Hitac expense document is fully paid, who paid it and
    # how is restricted to System Admin only.
    hitac_show_payments_button = fields.Boolean(compute='_compute_hitac_show_payments_button')

    @api.depends('payment_state', 'hitac_expense_type')
    @api.depends_context('uid')
    def _compute_hitac_show_payments_button(self):
        is_sys_admin = self.env.user.has_group('hitac_base.group_sys_admin')
        for move in self:
            move.hitac_show_payments_button = (
                is_sys_admin or move.payment_state != 'paid' or not move.hitac_expense_type
            )

    def _get_hitac_logo_b64(self):
        """Base64 of the HITAC emblem, embedded directly in the invoice
        report — wkhtmltopdf on this Windows install fails to fetch a
        root-relative static asset path (ProtocolUnknownError) when
        rendering from a local temp file, so a data: URI is used instead
        of a plain src. Mirrors sale.order's own copy of this helper —
        hitac_sales doesn't depend on hitac_base, so it's not shared."""
        with file_open('hitac_base/static/img/hitac.png', 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode()
