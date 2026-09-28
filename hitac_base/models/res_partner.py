# -*- coding: utf-8 -*-
from odoo import api, models, fields


HITAC_PARTNER_TYPES = [
    ('company', 'Company'),
    ('contact', 'Contact'),
    ('farm', 'Farm'),
    ('packing_house', 'Packing House'),
    ('supplier', 'Supplier'),
    ('freight_forwarder', 'Freight Forwarder'),
    ('shipping_line', 'Shipping Line'),
    ('drayage_company', 'Drayage Company'),
    ('employee', 'Employee'),
]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    hitac_type = fields.Selection(
        selection=HITAC_PARTNER_TYPES,
        string='Type',
        required=True,
        tracking=True,
    )

    @api.onchange('hitac_type')
    def _onchange_hitac_type(self):
        for partner in self:
            partner.is_company = partner.hitac_type != 'contact'
