# -*- coding: utf-8 -*-
{
    'name': 'Hitac Logistics',
    'version': '19.0.1.0.0',
    'summary': 'Shipments, containers and pallet loading for Hitac',
    'author': 'Islam Elsayed',
    'category': 'HITAC',
    'depends': [
        'hitac_base',
        'hitac_production',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'data/sequences.xml',
        'views/logistics_shipment_views.xml',
        'views/logistics_container_views.xml',
        'views/load_pallet_wizard_views.xml',
        'views/stock_pallet_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
