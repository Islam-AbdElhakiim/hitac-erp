from odoo import api, fields, models, _


class LogisticsShipment(models.Model):
    _name = 'logistics.shipment'
    _description = 'Shipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('in_transit', 'In Transit'),
            ('delivered', 'Delivered'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )
    departure_date = fields.Date(string='Departure Date')
    arrival_date = fields.Date(string='Arrival Date')
    container_ids = fields.One2many(
        'logistics.container',
        'shipment_id',
        string='Containers',
    )
    container_count = fields.Integer(
        string='Containers',
        compute='_compute_container_count',
    )

    @api.depends('container_ids')
    def _compute_container_count(self):
        for rec in self:
            rec.container_count = len(rec.container_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('logistics.shipment') or _('New')
        return super().create(vals_list)

    def action_transit(self):
        self.filtered(lambda r: r.state == 'draft').write({'state': 'in_transit'})

    def action_deliver(self):
        self.filtered(lambda r: r.state == 'in_transit').write({'state': 'delivered'})

    def action_reset(self):
        self.filtered(lambda r: r.state == 'in_transit').write({'state': 'draft'})

    def action_view_containers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Containers'),
            'res_model': 'logistics.container',
            'view_mode': 'list,form',
            'domain': [('shipment_id', '=', self.id)],
            'context': {'default_shipment_id': self.id},
        }
