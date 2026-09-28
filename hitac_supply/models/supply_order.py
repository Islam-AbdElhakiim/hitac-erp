from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SupplyOrder(models.Model):
    _name = 'supply.order'
    _description = 'Supply Order'
    _order = 'name desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    type = fields.Selection(
        selection=[('product', 'Product'), ('packaging', 'Packaging')],
        string='Type',
        required=True,
        default='product',
    )
    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('in_progress', 'In Progress'),
            ('received', 'Received'),
            ('returned', 'Returned'),
        ],
        string='Status',
        required=True,
        default='new',
    )
    has_return = fields.Boolean(string='Has Return', default=False)
    supplier_id = fields.Many2one(
        comodel_name='res.partner',
        string='Supplier',
        domain=[('hitac_type', '=', 'supplier')],
        required=True,
    )
    expected_date = fields.Date(string='Expected Date')
    packing_house_id = fields.Many2one(
        comodel_name='res.partner',
        string='Packing House',
        domain=[('hitac_type', '=', 'packing_house')],
    )
    sales_order_ids = fields.Many2many(
        comodel_name='sale.order',
        relation='supply_order_sale_rel',
        column1='supply_id',
        column2='sale_id',
        string='Sales Orders',
    )
    shipment_ids = fields.One2many(
        comodel_name='supply.shipment',
        inverse_name='supply_order_id',
        string='Shipments',
    )
    total_received_quantity = fields.Float(
        string='Total Received Qty',
        compute='_compute_total_received_quantity',
        store=True,
        digits='Product Unit of Measure',
    )

    @api.depends('shipment_ids.received_quantity', 'shipment_ids.is_return')
    def _compute_total_received_quantity(self):
        for order in self:
            order.total_received_quantity = sum(
                order.shipment_ids.filtered(lambda s: not s.is_return).mapped('received_quantity')
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('supply.order') or _('New')
        return super().create(vals_list)

    def action_set_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_set_received(self):
        for order in self:
            regular_shipments = order.shipment_ids.filtered(lambda s: not s.is_return)
            if not regular_shipments:
                raise ValidationError(_(
                    'Cannot mark "%s" as received: no shipments have been recorded.',
                    order.name,
                ))
            unfilled = regular_shipments.filtered(lambda s: not s.received_quantity)
            if unfilled:
                raise ValidationError(_(
                    'Cannot mark "%s" as received: received quantity is missing on: %s',
                    order.name,
                    ', '.join(unfilled.mapped('name')),
                ))
        self.write({'state': 'received'})

    def action_set_returned(self):
        self.write({'state': 'returned'})

    def action_reset_to_new(self):
        self.write({'state': 'new'})

    def action_create_return_shipment(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Return Shipment'),
            'res_model': 'supply.shipment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_supply_order_id': self.id,
                'default_is_return': True,
            },
        }
