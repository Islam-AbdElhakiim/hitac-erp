# -*- coding: utf-8 -*-
from odoo.addons.account.controllers.portal import PortalAccount as AccountCustomerPortal


class CustomerPortal(AccountCustomerPortal):

    def _show_report(self, model, report_type, report_ref, download=False):
        # portal_my_invoice_detail() resolves the preview/inline PDF via
        # invoice.partner_id.invoice_template_pdf_report_id, falling back to
        # the literal ref 'account.account_invoices' (base's own plain
        # invoice report) whenever that per-partner field isn't set — which
        # it never is here. That's a DIFFERENT field from the one hitac_base
        # sets on the Sales journal (account_journal.py's _register_hook),
        # so the already-generated/downloaded attachment uses hitac's
        # branded report while the live portal preview silently fell back
        # to the unbranded base one. Redirect that one specific ref, same
        # pattern as hitac_sales' own _show_report override for sale.order.
        if report_ref == 'account.account_invoices':
            report_ref = 'hitac_base.action_report_hitac_invoice'
        return super()._show_report(model, report_type, report_ref, download=download)
