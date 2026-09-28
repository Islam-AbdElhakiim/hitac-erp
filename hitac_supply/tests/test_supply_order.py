from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestSupplyOrder(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.supplier = cls.env['res.partner'].create({'name': 'Supplier A', 'hitac_type': 'supplier'})
        cls.product = cls.env['product.product'].create({'name': 'Mangoes'})

    def _create_order(self):
        return self.env['supply.order'].create({'supplier_id': self.supplier.id})

    def _create_shipment(self, order, received_quantity=0.0, is_return=False):
        return self.env['supply.shipment'].create({
            'supply_order_id': order.id,
            'product_id': self.product.id,
            'supplier_id': self.supplier.id,
            'received_quantity': received_quantity,
            'is_return': is_return,
        })

    def test_sequence_assigned_on_create(self):
        order = self._create_order()
        self.assertNotEqual(order.name, 'New')

    def test_cannot_receive_without_any_shipments(self):
        order = self._create_order()
        with self.assertRaises(ValidationError):
            order.action_set_received()

    def test_cannot_receive_with_missing_quantity(self):
        order = self._create_order()
        self._create_shipment(order, received_quantity=0.0)
        with self.assertRaises(ValidationError):
            order.action_set_received()

    def test_receive_succeeds_and_computes_total(self):
        order = self._create_order()
        self._create_shipment(order, received_quantity=100)
        order.action_set_received()
        self.assertEqual(order.state, 'received')
        self.assertEqual(order.total_received_quantity, 100)

    def test_return_shipments_excluded_from_total(self):
        order = self._create_order()
        self._create_shipment(order, received_quantity=100)
        self._create_shipment(order, received_quantity=20, is_return=True)
        self.assertEqual(order.total_received_quantity, 100)

    def test_state_transitions(self):
        order = self._create_order()
        order.action_set_in_progress()
        self.assertEqual(order.state, 'in_progress')
        order.action_reset_to_new()
        self.assertEqual(order.state, 'new')

    def test_create_return_shipment_action_prefills_context(self):
        order = self._create_order()
        action = order.action_create_return_shipment()
        self.assertEqual(action['res_model'], 'supply.shipment')
        self.assertEqual(action['context']['default_supply_order_id'], order.id)
        self.assertTrue(action['context']['default_is_return'])
