# -*- coding: utf-8 -*-
from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _register_hook(self):
        # Runs on every registry load (server start, module install/upgrade),
        # so it's self-healing across environments — no manual one-off data
        # fix needed. Only touches Sales journals that don't already have a
        # custom template set, so it never overwrites a deliberate choice.
        super()._register_hook()
        report = self.env.ref('hitac_base.action_report_hitac_invoice', raise_if_not_found=False)
        if not report:
            return
        sales_journals = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('invoice_template_pdf_report_id', '=', False),
        ])
        if sales_journals:
            sales_journals.invoice_template_pdf_report_id = report.id
