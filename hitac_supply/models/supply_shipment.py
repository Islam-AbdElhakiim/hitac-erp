from odoo import _, api, fields, models


class SupplyShipment(models.Model):
    _name = 'supply.shipment'
    _description = 'Supply Shipment'
    _order = 'expected_date desc, id desc'

    name = fields.Char(
        string='Reference',
        compute='_compute_name',
        store=True,
    )
    supply_order_id = fields.Many2one(
        comodel_name='supply.order',
        string='Supply Order',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
    )
    supplier_id = fields.Many2one(
        comodel_name='res.partner',
        string='Supplier',
        required=True,
        domain=[('supplier_rank', '>', 0)],
    )
    destination = fields.Char(string='Destination')
    expected_date = fields.Date(string='Expected Date')
    quantity = fields.Float(
        string='Quantity',
        digits='Product Unit of Measure',
        default=0.0,
    )
    received_quantity = fields.Float(
        string='Received Quantity',
        digits='Product Unit of Measure',
        default=0.0,
    )
    receiver_user_id = fields.Many2one(
        comodel_name='res.users',
        string='Receiver',
    )
    status = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('shipped', 'Shipped'),
            ('received', 'Received'),
            ('returned', 'Returned'),
        ],
        string='Status',
        required=True,
        default='pending',
    )
    is_return = fields.Boolean(string='Return Shipment', default=False)

    @api.depends('supply_order_id.name', 'product_id.name')
    def _compute_name(self):
        for rec in self:
            order = rec.supply_order_id.name or ''
            product = rec.product_id.name or ''
            if order and product:
                rec.name = f"{order} / {product}"
            else:
                rec.name = order or product or _('New Shipment')
