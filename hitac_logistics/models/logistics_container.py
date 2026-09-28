from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LogisticsContainer(models.Model):
    _name = 'logistics.container'
    _description = 'Shipping Container'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    shipment_id = fields.Many2one(
        'logistics.shipment',
        string='Shipment',
        ondelete='restrict',
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('open', 'Open'),
            ('sealed', 'Sealed'),
            ('shipped', 'Shipped'),
        ],
        string='Status',
        default='open',
        required=True,
        tracking=True,
    )
    pallet_ids = fields.One2many(
        'stock.pallet',
        'container_id',
        string='Pallets',
    )
    pallet_count = fields.Integer(
        string='Pallet Count',
        compute='_compute_pallet_count',
    )

    @api.depends('pallet_ids')
    def _compute_pallet_count(self):
        for rec in self:
            rec.pallet_count = len(rec.pallet_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('logistics.container') or _('New')
        return super().create(vals_list)

    def action_seal(self):
        self.filtered(lambda r: r.state == 'open').write({'state': 'sealed'})

    def action_ship(self):
        self.filtered(lambda r: r.state == 'sealed').write({'state': 'shipped'})

    def action_reopen(self):
        self.filtered(lambda r: r.state == 'sealed').write({'state': 'open'})

    def action_view_pallets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pallets'),
            'res_model': 'stock.pallet',
            'view_mode': 'list,form',
            'domain': [('container_id', '=', self.id)],
            'context': {'default_container_id': self.id},
        }

    def action_load_pallets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Load Pallets'),
            'res_model': 'logistics.load.pallet.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_container_id': self.id},
        }

    def _assign_pallets(self, pallets):
        """
        Load ready pallets into this container, or transfer already-loaded
        pallets from another container. Raises UserError on any constraint violation.
        """
        self.ensure_one()

        if not self.shipment_id:
            raise UserError(
                _('Container %s must be assigned to a shipment before loading pallets.') % self.name
            )
        if self.state != 'open':
            raise UserError(
                _('Container %s is %s and cannot accept pallets.') % (self.name, dict(self._fields['state'].selection).get(self.state))
            )

        invalid = pallets.filtered(lambda p: p.status not in ('ready', 'loaded'))
        if invalid:
            raise UserError(
                _('The following pallets must be in Ready status before loading:\n%s')
                % '\n'.join(invalid.mapped('name'))
            )

        already_here = pallets.filtered(lambda p: p.container_id.id == self.id)
        if already_here:
            raise UserError(
                _('The following pallets are already in this container:\n%s')
                % '\n'.join(already_here.mapped('name'))
            )

        pallets.write({
            'container_id': self.id,
            'status': 'loaded',
            'loaded_by': self.env.user.id,
            'loaded_at': fields.Datetime.now(),
        })
