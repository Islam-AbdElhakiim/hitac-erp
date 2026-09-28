from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    hitac_type = fields.Selection(
        selection=[('product', 'Product'), ('packaging', 'Packaging')],
        string='HITAC Type',
        default='product',
    )
