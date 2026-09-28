from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestProductionBatch(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.packing_house = cls.env['res.partner'].create({
            'name': 'Test Packing House',
            'hitac_type': 'packing_house',
        })
        cls.product = cls.env['product.product'].create({'name': 'Batch Product'})

    def _create_batch(self):
        return self.env['production.batch'].create({'packing_house_id': self.packing_house.id})

    def test_sequence_assigned_on_create(self):
        batch = self._create_batch()
        self.assertNotEqual(batch.name, 'New')

    def test_start_and_done_transitions(self):
        batch = self._create_batch()
        self.assertEqual(batch.state, 'draft')
        batch.action_start()
        self.assertEqual(batch.state, 'in_progress')
        batch.action_done()
        self.assertEqual(batch.state, 'done')

    def test_reset_only_affects_in_progress_batches(self):
        batch = self._create_batch()
        batch.action_start()
        batch.action_done()
        batch.action_reset()
        self.assertEqual(batch.state, 'done')  # already done, reset is a no-op

    def test_draft_batch_ignores_done(self):
        batch = self._create_batch()
        batch.action_done()
        self.assertEqual(batch.state, 'draft')  # done requires in_progress first

    def test_pallet_count_compute(self):
        batch = self._create_batch()
        self.env['stock.pallet'].create({'product_id': self.product.id, 'batch_id': batch.id})
        self.env['stock.pallet'].create({'product_id': self.product.id, 'batch_id': batch.id})
        self.assertEqual(batch.pallet_count, 2)
