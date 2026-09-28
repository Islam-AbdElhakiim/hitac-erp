# -*- coding: utf-8 -*-
from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _build_wkhtmltopdf_args(self, paperformat_id, landscape, specific_paperformat_args=None, set_viewport_size=False):
        command_args = super()._build_wkhtmltopdf_args(
            paperformat_id, landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size,
        )
        # This wkhtmltopdf/Windows install ignores the HTML's own <meta charset>
        # when loading a report from a local temp file and falls back to the
        # OS codepage, mangling non-ASCII bytes (Arabic text, accented
        # characters, the monetary widget's non-breaking space) into mojibake.
        # Force UTF-8 explicitly rather than relying on charset sniffing.
        command_args += ['--encoding', 'utf-8']
        return command_args
