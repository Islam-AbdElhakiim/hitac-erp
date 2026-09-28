{
    'name': 'Hitac Sales',
    'version': '19.0.1.0.0',
    'category': 'Hitac',
    'summary': 'Custom sales workflow with export/local order types and multi-stage tracking',
    'description': """
Hitac Sales extends Sale Order with:

- **Order Type**: Export or Local
- **Custom Workflow States**:
  - Quotation → Pro-forma (export only) → Confirmed
  - Confirmed → Supply (if supply required) → Production
  - Confirmed → Production (if no supply required)
  - Production → Shipping → Departed → Paid
- **Finance Fields**: Deposit tracking, Letter of Credit document
    """,
    'author': 'Hitac',
    'website': '',
    'depends': ['sale', 'hitac_base', 'hitac_supply'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'report/sale_order_report.xml',
        'data/mail_template_data.xml',
        'views/sale_order_views.xml',
        'views/sale_order_portal_templates.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hitac_sales/static/src/scss/ribbon.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
