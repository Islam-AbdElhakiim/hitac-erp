# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, _, fields, http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.sale.controllers.portal import CustomerPortal as SaleCustomerPortal


class CustomerPortal(SaleCustomerPortal):

    def _show_report(self, model, report_type, report_ref, download=False):
        # portal_order_page() hardcodes 'sale.action_report_saleorder' for the
        # sidebar's "View Details" link (?report_type=pdf/html); redirect that
        # one specific ref to our custom pro-forma/order report so it shows
        # the same document as the Print/Preview buttons.
        if report_ref == 'sale.action_report_saleorder':
            report_ref = 'hitac_sales.action_report_hitac_saleorder'
        return super()._show_report(model, report_type, report_ref, download=download)

    def _prepare_quotations_domain(self, partner):
        # Base 'sale' filters on state == 'sent', which no longer exists —
        # hitac_sales replaces the whole state selection. 'quotation' is the
        # only pre-confirmation stage in this workflow.
        domain = super()._prepare_quotations_domain(partner)
        return [d for d in domain if not (isinstance(d, (list, tuple)) and d[0] == 'state')] + [('state', '=', 'quotation')]

    def _prepare_orders_domain(self, partner):
        # Base 'sale' filters on state == 'sale'. Everything past Quotation
        # in hitac_sales' workflow (Pro-forma through Paid) counts as an
        # order for portal purposes.
        domain = super()._prepare_orders_domain(partner)
        return [d for d in domain if not (isinstance(d, (list, tuple)) and d[0] == 'state')] + [('state', '!=', 'quotation')]

    @http.route(['/my/orders/<int:order_id>'], type='http', auth="public", website=True)
    def portal_order_page(
        self,
        order_id,
        report_type=None,
        access_token=None,
        message=False,
        download=False,
        payment_amount=None,
        amount_selection=None,
        **kw
    ):
        # Full copy of sale.CustomerPortal.portal_order_page, with only the
        # history_session_key split changed below from base states
        # ('draft'/'sent'/'cancel', which don't exist here) to hitac_sales'
        # own 'quotation' vs. everything-else — keeps the "back to list"
        # navigation consistent with the domains above and the breadcrumb
        # fix in views/sale_order_portal_templates.xml. No smaller
        # extension point exists since this logic is inline in the route.
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        payment_amount = self._cast_as_float(payment_amount)
        prepayment_amount = order_sudo._get_prepayment_required_amount()
        if payment_amount and payment_amount < prepayment_amount and order_sudo.state != 'sale':
            raise MissingError(_("The amount is lower than the prepayment amount."))

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(
                model=order_sudo,
                report_type=report_type,
                report_ref='sale.action_report_saleorder',
                download=download,
            )

        # If the route is fetched from the link previewer avoid triggering that quotation is viewed.
        is_link_preview = request.httprequest.headers.get('Odoo-Link-Preview')
        if request.env.user.share and access_token and is_link_preview != 'True':
            # If a public/portal user accesses the order with the access token
            # Log a note on the chatter.
            today = fields.Date.today().isoformat()
            session_obj_date = request.session.get('view_quote_%s' % order_sudo.id)
            if session_obj_date != today:
                # store the date as a string in the session to allow serialization
                request.session['view_quote_%s' % order_sudo.id] = today
                # The "Quotation viewed by customer" log note is an information
                # dedicated to the salesman and shouldn't be translated in the customer/website lgg
                context = {'lang': order_sudo.user_id.partner_id.lang or order_sudo.company_id.partner_id.lang}
                author = order_sudo.partner_id if request.env.user._is_public() else request.env.user.partner_id
                msg = _('Quotation viewed by customer %s', author.name)
                del context
                order_sudo.with_user(SUPERUSER_ID).message_post(
                    body=msg,
                    message_type="notification",
                    subtype_xmlid="sale.mt_order_viewed",
                )

        backend_url = f'/odoo/action-{order_sudo._get_portal_return_action().id}/{order_sudo.id}'
        values = {
            'sale_order': order_sudo,
            'product_documents': order_sudo._get_product_documents(),
            'message': message,
            'report_type': 'html',
            'backend_url': backend_url,
            'res_company': order_sudo.company_id,  # Used to display correct company logo
            'payment_amount': payment_amount,
        }

        # Payment values
        if order_sudo._has_to_be_paid() or (payment_amount and not order_sudo.is_expired):
            values.update(self._get_payment_values(
                order_sudo,
                is_down_payment=self._determine_is_down_payment(
                    order_sudo, amount_selection, payment_amount
                ),
                payment_amount=payment_amount,
            ))
        else:
            values['payment_amount'] = None

        if order_sudo.state == 'quotation':
            history_session_key = 'my_quotations_history'
        else:
            history_session_key = 'my_orders_history'

        values = self._get_page_view_values(
            order_sudo, access_token, values, history_session_key, False, **kw)

        return request.render('sale.sale_order_portal_template', values)
