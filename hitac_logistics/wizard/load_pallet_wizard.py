from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LoadPalletWizard(models.TransientModel):
    _name = 'logistics.load.pallet.wizard'
    _description = 'Load Pallets into Container'

    container_id = fields.Many2one(
        'logistics.container',
        string='Container',
        required=True,
        readonly=True,
    )
    pallet_ids = fields.Many2many(
        'stock.pallet',
        string='Pallets to Load',
    )

    @api.onchange('container_id')
    def _onchange_container_id(self):
        if self.container_id:
            return {
                'domain': {
                    'pallet_ids': [
                        ('status', 'in', ['ready', 'loaded']),
                        ('container_id', '!=', self.container_id.id),
                    ]
                }
            }

    def action_load(self):
        self.ensure_one()
        if not self.pallet_ids:
            raise UserError(_('Please select at least one pallet.'))
        self.container_id._assign_pallets(self.pallet_ids)
        return {'type': 'ir.actions.act_window_close'}
