# -*- coding: utf-8 -*-
{
    'name': 'Hitac Marketing',
    'version': '19.0.1.0.0',
    'summary': 'Hitac branding and access control for Email Marketing',
    'author': 'Islam Elsayed',
    'category': 'HITAC',
    'depends': ['mass_mailing', 'hitac_base'],
    'data': [
        'security/marketing_groups.xml',
        'security/ir_rules.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
