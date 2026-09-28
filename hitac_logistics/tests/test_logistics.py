from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestLogisticsContainerLoading(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({'name': 'Logistics Product'})
        cls.shipment = cls.env['logistics.shipment'].create({})
        cls.container = cls.env['logistics.container'].create({'shipment_id': cls.shipment.id})

    def _create_pallet(self, status='ready'):
        return self.env['stock.pallet'].create({
            'product_id': self.product.id,
            'status': status,
        })

    def test_assign_requires_shipment(self):
        unassigned_container = self.env['logistics.container'].create({})
        pallet = self._create_pallet()
        with self.assertRaises(UserError):
            unassigned_container._assign_pallets(pallet)

    def test_assign_requires_open_state(self):
        pallet = self._create_pallet()
        self.container.action_seal()
        with self.assertRaises(UserError):
            self.container._assign_pallets(pallet)

    def test_assign_requires_ready_or_loaded_status(self):
        pallet = self._create_pallet(status='draft')
        with self.assertRaises(UserError):
            self.container._assign_pallets(pallet)

    def test_assign_success_updates_pallet(self):
        pallet = self._create_pallet()
        self.container._assign_pallets(pallet)
        self.assertEqual(pallet.status, 'loaded')
        self.assertEqual(pallet.container_id, self.container)
        self.assertTrue(pallet.loaded_by)
        self.assertTrue(pallet.loaded_at)

    def test_cannot_assign_pallet_already_in_this_container(self):
        pallet = self._create_pallet()
        self.container._assign_pallets(pallet)
        with self.assertRaises(UserError):
            self.container._assign_pallets(pallet)

    def test_unload_requires_loaded_status(self):
        pallet = self._create_pallet(status='draft')
        with self.assertRaises(UserError):
            pallet.action_unload()

    def test_unload_resets_pallet_state(self):
        pallet = self._create_pallet()
        self.container._assign_pallets(pallet)
        pallet.action_unload()
        self.assertEqual(pallet.status, 'ready')
        self.assertFalse(pallet.container_id)

    def test_seal_and_ship_transitions(self):
        self.container.action_seal()
        self.assertEqual(self.container.state, 'sealed')
        self.container.action_ship()
        self.assertEqual(self.container.state, 'shipped')

    def test_container_count_on_shipment(self):
        self.assertEqual(self.shipment.container_count, 1)
