import uuid

from odoo import api, fields, models, _


class StockPallet(models.Model):
    _name = 'stock.pallet'
    _description = 'Stock Pallet'
    _inherit = ['mail.thread']
    _order = 'id desc'

    _sql_constraints = [
        ('qr_code_unique', 'UNIQUE(qr_code)', 'QR code must be unique per pallet.'),
    ]

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )
    quantity = fields.Float(
        string='Quantity',
        required=True,
        default=1.0,
    )
    batch_id = fields.Many2one(
        'production.batch',
        string='Batch',
        ondelete='cascade',
    )
    # container_id is added by hitac_logistics via _inherit = 'stock.pallet'
    qr_code = fields.Char(
        string='QR Code',
        copy=False,
        readonly=True,
        index=True,
    )
    status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('ready', 'Ready'),
            ('loaded', 'Loaded'),
            ('shipped', 'Shipped'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )
    position_in_container = fields.Char(
        string='Position in Container',
    )
    loaded_by = fields.Many2one(
        'res.users',
        string='Loaded By',
    )
    loaded_at = fields.Datetime(
        string='Loaded At',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.pallet') or _('New')
            if not vals.get('qr_code'):
                vals['qr_code'] = uuid.uuid4().hex
        return super().create(vals_list)
