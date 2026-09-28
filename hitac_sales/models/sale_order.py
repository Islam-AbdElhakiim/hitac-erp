import base64

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import file_open, float_compare, float_is_zero

DEFAULT_VALIDITY_NOTE = 'Validity of Pro-forma invoice: three (3) days from date of issuing.'

# Threshold used everywhere invoice_status/order-lines-lock/header-lock need
# to know whether an order has moved past the editable quotation stage.
# Mirrors base Odoo's use of state == 'sale', which no longer exists here.
CONFIRMED_STATES = ('confirmed', 'supply', 'production', 'shipping', 'departed', 'paid')


HITAC_STATES = [
    ('quotation', 'Quotation'),
    ('proforma', 'Pro-forma'),
    ('confirmed', 'Confirmed'),
    ('supply', 'Supply'),
    ('production', 'Production'),
    ('shipping', 'Shipping'),
    ('departed', 'Departed'),
    ('paid', 'Paid'),
    ('cancelled', 'Cancelled'),
]

# States an order can still be cancelled from — anything before it has
# actually left the business (Departed/Paid are final; you can't cancel a
# shipment that's already gone or an order that's already been paid).
CANCELLABLE_STATES = ('quotation', 'proforma', 'confirmed', 'supply', 'production', 'shipping')


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    order_type = fields.Selection(
        selection=[('export', 'Export'), ('local', 'Local')],
        string='Order Type',
        default='export',
        required=True,
        tracking=True,
    )
    # Replaces the base state selection entirely with the Hitac workflow states.
    # Note: base methods like action_confirm() that reference 'draft'/'sale' states
    # are bypassed by replacing the header buttons in the view with our own actions.
    state = fields.Selection(
        selection=HITAC_STATES,
        string='Status',
        readonly=True,
        copy=False,
        index=True,
        tracking=3,
        default='quotation',
    )

    is_supply_required = fields.Boolean(string='Supply Required', tracking=True)
    supply_order_ids = fields.Many2many(
        comodel_name='supply.order',
        relation='supply_order_sale_rel',
        column1='sale_id',
        column2='supply_id',
        string='Supply Orders',
        tracking=True,
    )
    deposit_paid = fields.Boolean(string='Deposit Paid', tracking=True)
    deposit_amount = fields.Float(string='Deposit Amount', digits='Account')
    lc_issued = fields.Boolean(string='LC Issued', tracking=True)
    lc_document = fields.Binary(string='LC Document', attachment=True)
    lc_document_filename = fields.Char(string='LC Document Name')

    # -------------------------------------------------------------------------
    # Pro-forma / printable document fields
    # -------------------------------------------------------------------------

    country_of_origin = fields.Char(string='Country of Origin', default='Egypt')
    port_of_loading = fields.Char(string='Port of Loading (POL)')
    port_of_discharge = fields.Char(string='Port of Discharge (POD)')
    incoterm_code = fields.Char(string='Incoterms')
    buyer_contact_title = fields.Char(string='Buyer Contact Title', default='General Manager')
    buyer_contact_name = fields.Char(string='Buyer Contact Name')
    general_note = fields.Text(string='General Note')
    validity_note = fields.Text(string='Validity Note', default=DEFAULT_VALIDITY_NOTE)
    # Bumped each time a Pro-forma is (re)sent; combined with the order number
    # to form the printed PI No. (e.g. "S00023-01").
    pi_sequence = fields.Integer(string='PI Sequence', default=0, copy=False)
    pi_number = fields.Char(string='PI No.', compute='_compute_pi_number')
    total_carton_qty = fields.Integer(string='Total Cartons', compute='_compute_total_carton_qty')

    # -------------------------------------------------------------------------
    # Transport / shipping document fields
    # -------------------------------------------------------------------------

    vessel_name = fields.Char(string='Vessel / Flight Name')
    carrier_name = fields.Char(string='Carrier / Shipping Line')
    bl_number = fields.Char(string='Bill of Lading No.')
    bl_document = fields.Binary(string='B/L Document', attachment=True)
    bl_document_filename = fields.Char(string='B/L Document Name')
    etd_date = fields.Date(string='ETD (Estimated Departure)')
    eta_date = fields.Date(string='ETA (Estimated Arrival)')
    total_cbm = fields.Float(string='Total Volume (CBM)')
    customs_broker = fields.Char(string='Customs Broker')

    # -------------------------------------------------------------------------
    # Production placeholders — plain text for now, to be replaced with real
    # relations to production.batch / stock.pallet / logistics.container once
    # those cross-module links exist.
    # -------------------------------------------------------------------------

    packing_house = fields.Char(string='Packing House')
    batch_reference = fields.Char(string='Batch')
    containers_reference = fields.Char(string='Containers')
    production_responsible = fields.Char(string='Responsible')
    production_notes = fields.Text(string='Production Notes')

    @api.depends('name', 'pi_sequence')
    def _compute_pi_number(self):
        for order in self:
            order.pi_number = f'{order.name}-{order.pi_sequence:02d}' if order.pi_sequence else order.name

    @api.depends('order_line.carton_qty')
    def _compute_total_carton_qty(self):
        for order in self:
            order.total_carton_qty = sum(order.order_line.mapped('carton_qty'))

    @api.depends('state', 'order_line.invoice_status')
    def _compute_invoice_status(self):
        """Full copy of sale.order's own _compute_invoice_status, with only
        the state == 'sale' checks swapped for CONFIRMED_STATES — that base
        value doesn't exist under hitac_sales' own state field, so every
        order was permanently stuck at invoice_status == 'no' regardless of
        actual stage or invoiced quantities."""
        confirmed_orders = self.filtered(lambda so: so.state in CONFIRMED_STATES)
        (self - confirmed_orders).invoice_status = 'no'
        if not confirmed_orders:
            return
        lines_domain = [('is_downpayment', '=', False), ('display_type', '=', False)]
        line_invoice_status_all = [
            (order.id, invoice_status)
            for order, invoice_status in self.env['sale.order.line']._read_group(
                lines_domain + [('order_id', 'in', confirmed_orders.ids)],
                ['order_id', 'invoice_status']
            )
        ]
        for order in confirmed_orders:
            line_invoice_status = [d[1] for d in line_invoice_status_all if d[0] == order.id]
            if order.state not in CONFIRMED_STATES:
                order.invoice_status = 'no'
            elif any(invoice_status == 'to invoice' for invoice_status in line_invoice_status):
                if any(invoice_status == 'no' for invoice_status in line_invoice_status):
                    # If only discount/delivery/promotion lines can be invoiced, the SO should not
                    # be invoiceable.
                    invoiceable_domain = lines_domain + [('invoice_status', '=', 'to invoice')]
                    invoiceable_lines = order.order_line.filtered_domain(invoiceable_domain)
                    special_lines = invoiceable_lines.filtered(
                        lambda sol: not sol._can_be_invoiced_alone()
                    )
                    if invoiceable_lines == special_lines:
                        order.invoice_status = 'no'
                    else:
                        order.invoice_status = 'to invoice'
                else:
                    order.invoice_status = 'to invoice'
            elif line_invoice_status and all(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                order.invoice_status = 'invoiced'
            elif line_invoice_status and all(invoice_status in ('invoiced', 'upselling') for invoice_status in line_invoice_status):
                order.invoice_status = 'upselling'
            else:
                order.invoice_status = 'no'

    def _get_hitac_logo_b64(self):
        """Base64 of the HITAC emblem, embedded directly in the pro-forma
        report — wkhtmltopdf on Windows fails to fetch a root-relative
        static asset path (ProtocolUnknownError) when rendering from a
        local temp file, so a data: URI is used instead of a plain src."""
        with file_open('hitac_base/static/img/hitac.png', 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode()

    @api.constrains('order_line')
    def _check_order_line_required(self):
        for order in self:
            if not order.order_line:
                raise ValidationError(_('An order must have at least one order line.'))

    @api.model_create_multi
    def create(self, vals_list):
        """@api.constrains only re-validates fields that were actually keys
        in vals — a plain create() with no 'order_line' key at all (e.g. just
        partner_id/order_type) never touches that key, so
        _check_order_line_required above silently never fires for it. Force
        the check unconditionally right after creation instead."""
        orders = super().create(vals_list)
        orders._check_order_line_required()
        return orders

    def _find_mail_template(self):
        """Override of sale.order's own _find_mail_template. Base's version
        (addons/sale/models/sale_order.py) checks `self.state != 'sale'` to
        decide between the quotation and confirmation templates — 'sale'
        never exists under hitac_sales' own state field, so that branch
        always fired regardless of actual stage, and always returned base's
        own email_template_edi_sale/email_template_proforma, whose attached
        report is base's plain sale.action_report_saleorder — never hitac's
        branded pro-forma/order report. Mirrors the same context.get('proforma')
        switch base uses, just pointing at hitac's own templates."""
        self.ensure_one()
        if self.env.context.get('proforma'):
            return self.env.ref('hitac_sales.email_template_hitac_proforma', raise_if_not_found=False)
        return self.env.ref('hitac_sales.email_template_hitac_quotation', raise_if_not_found=False)

    # -------------------------------------------------------------------------
    # State transition actions
    # -------------------------------------------------------------------------

    def action_send_proforma(self):
        """Quotation → Pro-forma (export orders only)."""
        for order in self:
            if order.order_type != 'export':
                raise UserError(_('Pro-forma invoices are only applicable to Export orders.'))
            if order.state != 'quotation':
                raise UserError(_('Only a Quotation can be sent as a Pro-forma.'))
            order.write({'state': 'proforma', 'pi_sequence': order.pi_sequence + 1})

    def action_confirm_order(self):
        """
        Quotation → Confirmed  (Local orders)
        Pro-forma → Confirmed  (Export orders)
        """
        for order in self:
            is_local_ready = order.order_type == 'local' and order.state == 'quotation'
            is_export_ready = order.order_type == 'export' and order.state == 'proforma'
            if not (is_local_ready or is_export_ready):
                raise UserError(_(
                    "Cannot confirm this order.\n"
                    "Local orders must be in 'Quotation' state.\n"
                    "Export orders must be in 'Pro-forma' state."
                ))
            order.write({'state': 'confirmed'})

    def action_to_supply(self):
        """Confirmed → Supply (only when supply is required)."""
        for order in self:
            if order.state != 'confirmed':
                raise UserError(_('Only a Confirmed order can move to Supply.'))
            if not order.is_supply_required:
                raise UserError(_(
                    'Supply is not required for this order. '
                    'Use "To Production" instead.'
                ))
            order.write({'state': 'supply'})

    def action_to_production(self):
        """
        Confirmed → Production  (when supply is NOT required)
        Supply    → Production  (after supply is complete)
        """
        for order in self:
            if order.state == 'confirmed' and order.is_supply_required:
                raise UserError(_(
                    'This order requires a Supply stage. '
                    'Please use "To Supply" first.'
                ))
            if order.state not in ('confirmed', 'supply'):
                raise UserError(_('Order must be in Confirmed or Supply state to move to Production.'))
            if order.state == 'supply' and not order.supply_order_ids:
                raise UserError(_('Link at least one Supply Order before moving to Production.'))
            order.write({'state': 'production'})

    def action_to_shipping(self):
        """Production → Shipping."""
        for order in self:
            if order.state != 'production':
                raise UserError(_('Order must be in Production state to move to Shipping.'))
            order.write({'state': 'shipping'})

    def action_to_departed(self):
        """Shipping → Departed."""
        for order in self:
            if order.state != 'shipping':
                raise UserError(_('Order must be in Shipping state to mark as Departed.'))
            order.write({'state': 'departed'})

    def action_to_paid(self):
        """Departed → Paid."""
        for order in self:
            if order.state != 'departed':
                raise UserError(_('Order must be in Departed state to mark as Paid.'))
            order.write({'state': 'paid'})

    def action_reset_to_draft(self):
        """Reset a Quotation, Pro-forma, Confirmed, or Cancelled order back
        to Quotation (soft undo / reactivation) — also re-opens the order
        lines for editing, since they're locked from Confirmed onward."""
        for order in self:
            if order.state not in ('quotation', 'proforma', 'confirmed', 'cancelled'):
                raise UserError(_('Only a Quotation, Pro-forma, Confirmed, or Cancelled order can be reset.'))
            order.write({'state': 'quotation'})

    def action_cancel_order(self):
        """Cancel an order that hasn't Departed or been Paid yet — once
        goods have actually left or money has actually been received,
        cancelling retroactively no longer makes sense; use the Reset
        buttons to step back through the pipeline instead."""
        for order in self:
            if order.state not in CANCELLABLE_STATES:
                raise UserError(_(
                    'Only orders that have not yet Departed or been Paid can be cancelled. '
                    'Use one of the "Reset to..." buttons to step back through the pipeline first.'
                ))
            order.write({'state': 'cancelled'})

    def _action_cancel(self):
        """Override of sale.order's own _action_cancel — invoked by base's
        bulk "Cancel" wizard (sale.mass.cancel.orders), bound to the list/
        kanban Actions menu. Base ends with self.write({'state': 'cancel'}),
        a value that doesn't exist under hitac_sales' own state field
        (spelled 'cancelled'), which raised a ValueError from the grid's
        bulk Cancel action. Mirrors action_cancel_order's CANCELLABLE_STATES
        validation, keeps base's draft-invoice cleanup."""
        if any(order.state not in CANCELLABLE_STATES for order in self):
            raise UserError(_(
                'Only orders that have not yet Departed or been Paid can be cancelled. '
                'Use one of the "Reset to..." buttons to step back through the pipeline first.'
            ))
        inv = self.invoice_ids.filtered(lambda inv: inv.state == 'draft')
        inv.button_cancel()
        return self.write({'state': 'cancelled'})

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_cancel(self):
        """Override of sale.order's own @api.ondelete hook of the same name
        (not a plain unlink() override — that's why a grep for "def unlink"
        won't find it). Base checks state not in ('draft', 'cancel'), and
        neither value exists under hitac_sales' own state field — meaning
        it was IMPOSSIBLE to delete any hitac order, including a properly
        Cancelled one, since our state is spelled 'cancelled', not 'cancel'.
        Mirrors base's semantics one-for-one: quotation (never confirmed) and
        cancelled are deletable; everything else, including Pro-forma, is
        not."""
        for order in self:
            if order.state not in ('quotation', 'cancelled'):
                raise UserError(_(
                    "You cannot delete a Pro-forma or a confirmed sales order. "
                    "You must first cancel it."
                ))

    def action_reset_to_confirmed(self):
        """Supply → Confirmed, or Production → Confirmed when this order
        skipped Supply (soft undo; order lines stay locked, this is not a
        return to editable Quotation). When Production was reached via
        Supply, use action_reset_to_supply() instead — that's the order's
        actual previous step."""
        for order in self:
            valid = order.state == 'supply' or (order.state == 'production' and not order.is_supply_required)
            if not valid:
                raise UserError(_(
                    'Only a Supply order, or a Production order that did not go through Supply, '
                    'can be reset to Confirmed.'
                ))
            order.write({'state': 'confirmed'})

    def action_reset_to_supply(self):
        """Production → Supply (soft undo), for orders that actually went
        through Supply — mirrors action_to_production()'s own routing."""
        for order in self:
            if order.state != 'production':
                raise UserError(_('Only a Production order can be reset to Supply.'))
            if not order.is_supply_required:
                raise UserError(_('This order did not go through Supply. Use "Reset to Confirmed" instead.'))
            order.write({'state': 'supply'})

    def action_reset_to_production(self):
        """Shipping → Production (soft undo)."""
        for order in self:
            if order.state != 'shipping':
                raise UserError(_('Only a Shipping order can be reset to Production.'))
            order.write({'state': 'production'})

    def action_reset_to_shipping(self):
        """Departed → Shipping (soft undo)."""
        for order in self:
            if order.state != 'departed':
                raise UserError(_('Only a Departed order can be reset to Shipping.'))
            order.write({'state': 'shipping'})

    def action_reset_to_departed(self):
        """Paid → Departed (soft undo)."""
        for order in self:
            if order.state != 'paid':
                raise UserError(_('Only a Paid order can be reset to Departed.'))
            order.write({'state': 'departed'})

    def _get_name_portal_content_view(self):
        """The customer-portal page (opened by the header's Preview button
        via the base action_preview_sale_order/get_portal_url) should show
        the same pro-forma/order document as the Print button, instead of
        the base module's generic quotation layout."""
        self.ensure_one()
        return 'hitac_sales.portal_content_hitac'

    # -------------------------------------------------------------------------
    # sale_stock integration — disabled until hitac_logistics implements it
    # -------------------------------------------------------------------------

    def _action_confirm(self):
        # Do NOT call super — sale_stock's override would launch procurement rules.
        # Picking creation is owned by hitac_logistics.
        pass

    def _compute_picking_ids(self):
        for order in self:
            order.delivery_count = 0

    def _compute_delivery_status(self):
        # Disabled — no pickings are created by the sale workflow.
        for order in self:
            order.delivery_status = False

    def _check_warehouse(self):
        # Disabled — warehouse linkage is managed by hitac_logistics, not hitac_sales.
        pass


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    packing_type = fields.Char(string='Packing', default='Cartons')
    carton_qty = fields.Integer(string='Cartons')
    net_weight = fields.Float(string='Net Weight (Kg)')
    gross_weight = fields.Float(string='Gross Weight (Kg)')

    def _action_launch_stock_rule(self, **kwargs):
        # Disabled — picking creation is owned by hitac_logistics.
        return True

    def _check_line_unlink(self):
        """Override of sale.order.line's own check (line.state == 'sale',
        which never matches under hitac_sales' own state field). This one
        runs the opposite direction from the order-level ondelete fix above:
        it was too PERMISSIVE rather than too restrictive — it silently
        never blocked deleting a line via API/RPC even on a Confirmed+
        order. The order_line widget's own readonly (see views) already
        stops this in the UI, but this closes the same gap at the model
        level for anything that bypasses the form."""
        return self.filtered(
            lambda line:
                line.state in CONFIRMED_STATES
                and (line.invoice_lines or not line.is_downpayment)
                and not line.display_type
        )

    # no trigger product_id.invoice_policy to avoid retroactively changing SO
    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'state')
    def _compute_qty_to_invoice(self):
        """Full copy of sale.order.line's own _compute_qty_to_invoice, with
        only the state == 'sale' check swapped for CONFIRMED_STATES — this
        one sits upstream of invoice_status below: with the base version,
        qty_to_invoice was hardcoded to 0 for every hitac order regardless
        of quantities, which alone would have kept invoice_status stuck at
        'no' even after fixing that compute directly."""
        combo_lines = set()
        for line in self:
            if line.state in CONFIRMED_STATES and not line.display_type:
                if line.product_id.type == 'combo':
                    combo_lines.add(line)
                elif line.product_id.invoice_policy == 'order':
                    line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_delivered - line.qty_invoiced
                if line.combo_item_id and line.linked_line_id:
                    combo_lines.add(line.linked_line_id)
            else:
                line.qty_to_invoice = 0
        for combo_line in combo_lines:
            if any(
                line.combo_item_id and line.qty_to_invoice
                for line in combo_line.linked_line_ids
            ):
                combo_line.qty_to_invoice = combo_line.product_uom_qty - combo_line.qty_invoiced
            else:
                combo_line.qty_to_invoice = 0

    @api.depends('state', 'product_uom_qty', 'qty_delivered', 'qty_to_invoice', 'qty_invoiced')
    def _compute_invoice_status(self):
        """Full copy of sale.order.line's own _compute_invoice_status, with
        only the state == 'sale' checks swapped for CONFIRMED_STATES — see
        the order-level override above for why."""
        precision = self.env['decimal.precision'].precision_get('Product Unit')
        for line in self:
            if line.state not in CONFIRMED_STATES:
                line.invoice_status = 'no'
            elif line.is_downpayment and line.untaxed_amount_to_invoice == 0:
                line.invoice_status = 'invoiced'
            elif not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                line.invoice_status = 'to invoice'
            elif line.state in CONFIRMED_STATES and line.product_id.invoice_policy == 'order' and\
                    line.product_uom_qty >= 0.0 and\
                    float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=precision) == 1:
                line.invoice_status = 'upselling'
            elif float_compare(line.qty_invoiced, line.product_uom_qty, precision_digits=precision) >= 0:
                line.invoice_status = 'invoiced'
            else:
                line.invoice_status = 'no'
