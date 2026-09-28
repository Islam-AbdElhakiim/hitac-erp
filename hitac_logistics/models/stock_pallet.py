from odoo import fields, models, _
from odoo.exceptions import UserError


class StockPallet(models.Model):
    _inherit = 'stock.pallet'

    container_id = fields.Many2one(
        'logistics.container',
        string='Container',
        ondelete='set null',
        tracking=True,
    )

    def action_unload(self):
        loaded = self.filtered(lambda p: p.status == 'loaded')
        if not loaded:
            raise UserError(_('Only loaded pallets can be unloaded.'))
        loaded.write({
            'container_id': False,
            'status': 'ready',
            'loaded_by': False,
            'loaded_at': False,
        })
