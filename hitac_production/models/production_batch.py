from odoo import api, fields, models, _


class ProductionBatch(models.Model):
    _name = 'production.batch'
    _description = 'Production Batch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    type = fields.Selection(
        selection=[('export', 'Export'), ('local', 'Local')],
        string='Type',
        required=True,
        default='local',
        tracking=True,
    )
    packing_house_id = fields.Many2one(
        'res.partner',
        string='Packing House',
        domain=[('hitac_type', '=', 'packing_house')],
        required=True,
    )
    responsible_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        required=True,
    )
    sales_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )
    pallet_ids = fields.One2many(
        'stock.pallet',
        'batch_id',
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
                vals['name'] = self.env['ir.sequence'].next_by_code('production.batch') or _('New')
        return super().create(vals_list)

    def action_start(self):
        self.filtered(lambda r: r.state == 'draft').write({'state': 'in_progress'})

    def action_done(self):
        self.filtered(lambda r: r.state == 'in_progress').write({'state': 'done'})

    def action_reset(self):
        self.filtered(lambda r: r.state == 'in_progress').write({'state': 'draft'})

    def action_view_pallets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pallets'),
            'res_model': 'stock.pallet',
            'view_mode': 'list,form',
            'domain': [('batch_id', '=', self.id)],
            'context': {'default_batch_id': self.id},
        }
