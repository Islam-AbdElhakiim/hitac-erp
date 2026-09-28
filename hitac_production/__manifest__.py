# -*- coding: utf-8 -*-
{
    'name': 'Hitac Production',
    'version': '19.0.1.0.0',
    'summary': 'Production batch and pallet tracking for Hitac',
    'author': 'Islam Elsayed',
    'category': 'HITAC',
    'depends': [
        'hitac_base',
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'data/sequences.xml',
        'views/production_batch_views.xml',
        'views/stock_pallet_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
