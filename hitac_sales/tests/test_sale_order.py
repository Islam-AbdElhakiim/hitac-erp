from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestSaleOrderWorkflow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Buyer',
            'hitac_type': 'company',
        })
        cls.supplier = cls.env['res.partner'].create({
            'name': 'Test Supplier',
            'hitac_type': 'supplier',
        })
        cls.product = cls.env['product.product'].create({'name': 'Test Export Product'})

    def _create_order(self, order_type):
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_type': order_type,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 10,
            })],
        })

    def test_local_order_skips_proforma(self):
        order = self._create_order('local')
        self.assertEqual(order.state, 'quotation')
        order.action_confirm_order()
        self.assertEqual(order.state, 'confirmed')

    def test_export_order_requires_proforma_first(self):
        order = self._create_order('export')
        with self.assertRaises(UserError):
            order.action_confirm_order()
        order.action_send_proforma()
        self.assertEqual(order.state, 'proforma')
        order.action_confirm_order()
        self.assertEqual(order.state, 'confirmed')

    def test_proforma_is_export_only(self):
        order = self._create_order('local')
        with self.assertRaises(UserError):
            order.action_send_proforma()

    def test_pi_sequence_bumps_on_each_proforma(self):
        order = self._create_order('export')
        order.action_send_proforma()
        self.assertEqual(order.pi_sequence, 1)
        order.action_reset_to_draft()
        order.action_send_proforma()
        self.assertEqual(order.pi_sequence, 2)
        self.assertTrue(order.pi_number.endswith('-02'))

    def test_supply_required_flow_needs_supply_order_linked(self):
        order = self._create_order('local')
        order.is_supply_required = True
        order.action_confirm_order()

        with self.assertRaises(UserError):
            order.action_to_production()  # must go through Supply first

        order.action_to_supply()
        self.assertEqual(order.state, 'supply')

        with self.assertRaises(UserError):
            order.action_to_production()  # no supply order linked yet

        supply_order = self.env['supply.order'].create({'supplier_id': self.supplier.id})
        order.supply_order_ids = [(4, supply_order.id)]
        order.action_to_production()
        self.assertEqual(order.state, 'production')

    def test_no_supply_required_skips_supply_stage(self):
        order = self._create_order('local')
        order.action_confirm_order()
        with self.assertRaises(UserError):
            order.action_to_supply()
        order.action_to_production()
        self.assertEqual(order.state, 'production')

    def test_full_happy_path_to_paid(self):
        order = self._create_order('local')
        order.action_confirm_order()
        order.action_to_production()
        order.action_to_shipping()
        order.action_to_departed()
        order.action_to_paid()
        self.assertEqual(order.state, 'paid')

    def test_reset_to_draft_blocked_past_confirmed(self):
        order = self._create_order('local')
        order.action_confirm_order()
        order.action_to_production()
        with self.assertRaises(UserError):
            order.action_reset_to_draft()

    def test_reset_to_supply_requires_supply_stage(self):
        order = self._create_order('local')
        order.action_confirm_order()
        order.action_to_production()
        with self.assertRaises(UserError):
            order.action_reset_to_supply()

    def test_total_carton_qty_compute(self):
        order = self._create_order('local')
        order.order_line.carton_qty = 5
        self.assertEqual(order.total_carton_qty, 5)
