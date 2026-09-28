# -*- coding: utf-8 -*-
{
    'name': 'Hitac Base',
    'version': '19.0.1.0.0',
    'summary': 'Controlled ERP environment for Hitac',
    'author': 'Islam Elsayed',
    'category': 'HITAC',
    'depends': [
        'base',
        'web',
        'account',
        'calendar',
        'contacts',
        'mail',
        'portal',
        'sale',
        'utm',
        'spreadsheet_dashboard',
    ],
    'data': [
        'security/hitac_groups.xml',
        'security/ir.model.access.csv',
        'views/menu_overrides.xml',
        'views/res_partner_views.xml',
        'views/res_users_views.xml',
        'views/report_layout_overrides.xml',
        'views/portal_branding_overrides.xml',
        'views/account_move_views.xml',
        'views/invoicing_menus.xml',
        'data/report_paperformat.xml',
        'report/account_invoice_report.xml',
        'views/webclient_branding.xml',
        'data/hitac_bot_data.xml',
    ],
    'assets': {
        # Loads after Odoo's own primary variables (and after every dependency's),
        # so the brand color reaches the navbar and the loading indicator.
        'web._assets_primary_variables': [
            'hitac_base/static/src/scss/primary_variables.scss',
        ],
        'web.assets_backend': [
            'hitac_base/static/src/scss/btn_primary.scss',
        ],
        # Login page runs on the frontend bundle, not the backend one —
        # same button-color override plus the login-card accent.
        'web.assets_frontend': [
            'hitac_base/static/src/scss/btn_primary.scss',
            'hitac_base/static/src/scss/login.scss',
        ],
        # The portal chatter (customer-portal "Communication history" widget)
        # renders inside a shadow DOM that only loads this dedicated bundle —
        # a rule added to web.assets_frontend never reaches it, since shadow
        # roots don't inherit the main document's stylesheets.
        'portal.assets_chatter_style': [
            'hitac_base/static/src/scss/portal_chatter.scss',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
