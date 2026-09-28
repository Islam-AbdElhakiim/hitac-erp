from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestStockPallet(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({'name': 'Pallet Product'})

    def test_sequence_and_qr_code_assigned_on_create(self):
        pallet = self.env['stock.pallet'].create({'product_id': self.product.id})
        self.assertNotEqual(pallet.name, 'New')
        self.assertTrue(pallet.qr_code)

    def test_qr_code_unique_per_pallet(self):
        pallet_a = self.env['stock.pallet'].create({'product_id': self.product.id})
        pallet_b = self.env['stock.pallet'].create({'product_id': self.product.id})
        self.assertNotEqual(pallet_a.qr_code, pallet_b.qr_code)

    def test_explicit_qr_code_is_kept(self):
        pallet = self.env['stock.pallet'].create({
            'product_id': self.product.id,
            'qr_code': 'custom-qr-123',
        })
        self.assertEqual(pallet.qr_code, 'custom-qr-123')
