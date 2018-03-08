# -*- coding: utf-8 -*-
# Copyright 2016, Jarsa Sistemas, S.A. de C.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import Warning
from datetime import datetime
import calendar
import json
from odoo.tools import config
from odoo.tools.misc import xlwt


class TMSReportContextCommon(models.TransientModel):
    _name = "kardex.report.context.common"
    _description = "A particular context for a financial report"

    date_from = fields.Date("Start date")
    date_to = fields.Date("End date")

    @api.model
    def get_context_by_report_name(self, name):
        return self.env[self._report_name_to_report_context()[name]]

    @api.model
    def get_context_name_by_report_name_json(self):
        return json.dumps(self._report_name_to_report_context())

    @api.model
    def get_context_name_by_report_model_json(self):
        return json.dumps(self._report_model_to_report_context())

    def _report_name_to_report_model(self):
        return {
            'manager_ledger': 'kardex.manager.ledger',
        }

    def _report_model_to_report_context(self):
        return {
            'kardex.manager.ledger': 'kardex.context.manager.ledger',
        }

    def _report_name_to_report_context(self):
        return dict([(k[0], self._report_model_to_report_context()[k[1]]) for
                    k in self._report_name_to_report_model().items()])

    @api.model
    def get_full_report_name_by_report_name(self, name):
        return self._report_name_to_report_model()[name]

    def get_report_obj(self):
        raise Warning(_('get_report_obj not implemented'))

    @api.multi
    def remove_line(self, line_id):
        self.write({self.fold_field: [(3, line_id)]})

    @api.multi
    def add_line(self, line_id):
        self.write({self.fold_field: [(4, line_id)]})

    @api.multi
    def set_next_number(self, num):
        self.write({'next_footnote_number': num})
        return

    def get_columns_names(self):
        raise Warning(_('get_columns_names not implemented'))

    def get_full_date_names(self, dt_to, dt_from=None):
        convert_date = self.env['ir.qweb.field.date'].value_to_html
        date_to = convert_date(dt_to, None)
        dt_to = datetime.strptime(dt_to, "%Y-%m-%d")
        if dt_from:
            date_from = convert_date(dt_from, None)
        if not dt_from:
            return _('(As of %s)') % (date_to,)
        return _('(From %s <br/> to  %s)') % (date_from, date_to)

    @api.model
    def _get_footnotes(self, type, target_id):
        footnotes = self.footnotes.filtered(
            lambda s: s.type == type and s.target_id == target_id)
        result = {}
        for footnote in footnotes:
            result.update({footnote.column: footnote.number})
        return result

    @api.model
    def create(self, vals):
        res = super(TMSReportContextCommon, self).create(vals)
        report_type = res.get_report_obj().get_report_type()
        if report_type in ['date_range']:
            dt = datetime.today()
            update = {
                'date_from': datetime.today().replace(day=1, month=1),
                'date_to': dt.replace(
                    day=calendar.monthrange(dt.year, dt.month)[1]),
            }
        res.write(update)
        return res

    @api.model
    def get_pdf(self):
        if not config['test_enable']:
            self = self.with_context(commit_assetsbundle=True)

        report_obj = self.get_report_obj()
        lines = report_obj.with_context(print_mode=True).get_lines(self)
        footnotes = []
        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.user.company_id,
        }

        body = self.env['ir.ui.view'].render_template(
            "stock_kardex.main_kardex_general_report_letter",
            values=dict(rcontext, lines=lines, footnotes=footnotes, report=report_obj, context=self),
        )

        header = self.env['report'].render(
            "report.internal_layout",
            values=rcontext,
        )
        header = self.env['report'].render(
            "report.minimal_layout",
            values=dict(rcontext, subst=True, body=header),
        )

        landscape = False
        if len(self.get_columns_names()) > 4:
            landscape = True

        return self.env['report']._run_wkhtmltopdf([header], [''], [(0, body)], landscape, self.env.user.company_id.paperformat_id, spec_paperformat_args={'data-report-margin-top': 10, 'data-report-header-spacing': 10})

    @api.multi
    def get_html_and_data(self, given_context=None):
        if given_context is None:
            given_context = {}
        result = {}
        if given_context:
            update = {}
            for field in given_context:
                if field.startswith('add_'):
                    update[field[4:]] = [(4, int(given_context[field]))]
                if field.startswith('remove_'):
                    update[field[7:]] = [(3, int(given_context[field]))]
                if (self._fields.get(field) and
                        given_context[field] != 'undefined'):
                    if given_context[field] == 'false':
                        given_context[field] = False
                    if given_context[field] == 'none':
                        given_context[field] = None
                    if field == 'company_ids':
                        update[field] = [(6, 0, given_context[field])]
                    else:
                        update[field] = given_context[field]

            self.write(update)
        lines = self.get_report_obj().get_lines(self)
        rcontext = {
            'res_company': self.env['res.users'].browse(
                self.env.uid).company_id,
            'context': self,
            'report': self.get_report_obj(),
            'lines': lines,
            'mode': 'display',
        }
        result['html'] = self.env['ir.model.data'].xmlid_to_object(
            self.get_report_obj().get_template()).render(rcontext)
        result['report_type'] = self.get_report_obj().get_report_type()
        select = ['id', 'date_filter', 'date_from', 'date_to']
        result['report_context'] = self.read(select)[0]
        if self.get_report_obj().get_name() == 'manager_ledger':
            result['report_context']['available_filter_product_ids'] = self.get_available_filter_product_ids_names()
            result['report_context']['filter_product_ids'] = [(t.id, t.code, t.name) for t in self.filter_product_ids]
        return result

    def get_xls(self, response):
        book = xlwt.Workbook()
        report_id = self.get_report_obj()
        sheet = book.add_sheet(report_id.get_title())

        title_style = xlwt.easyxf(
            'font: bold true; borders: bottom medium;',
            num_format_str='#,##0.00')
        level_0_style = xlwt.easyxf(
            ('font: bold true; borders: bottom medium, top medium; '
                'pattern: pattern solid, fore-colour grey25;'),
            num_format_str='#,##0.00')
        level_0_style_left = xlwt.easyxf(
            ('font: bold true; borders: bottom medium, top medium, '
                'left medium; pattern: pattern solid, fore-colour grey25;'),
            num_format_str='#,##0.00')
        level_0_style_right = xlwt.easyxf(
            ('font: bold true; borders: bottom medium, top medium, '
                'right medium; pattern: pattern solid, fore-colour grey25;'),
            num_format_str='#,##0.00')
        level_1_style = xlwt.easyxf(
            'font: bold true; borders: bottom medium, top medium;',
            num_format_str='#,##0.00')
        level_1_style_left = xlwt.easyxf(
            ('font: bold true; borders: bottom medium, '
                'top medium, left medium;'), num_format_str='#,##0.00')
        level_1_style_right = xlwt.easyxf(
            ('font: bold true; borders: bottom medium, '
                'top medium, right medium;'), num_format_str='#,##0.00')
        level_2_style = xlwt.easyxf(
            'font: bold true; borders: top medium;', num_format_str='#,##0.00')
        level_2_style_left = xlwt.easyxf(
            'font: bold true; borders: top medium, left medium;',
            num_format_str='#,##0.00')
        level_2_style_right = xlwt.easyxf(
            'font: bold true; borders: top medium, right medium;',
            num_format_str='#,##0.00')
        level_3_style = xlwt.easyxf(num_format_str='#,##0.00')
        level_3_style_left = xlwt.easyxf(
            'borders: left medium;', num_format_str='#,##0.00')
        level_3_style_right = xlwt.easyxf(
            'borders: right medium;', num_format_str='#,##0.00')
        domain_style = xlwt.easyxf(
            'font: italic true;', num_format_str='#,##0.00')
        domain_style_left = xlwt.easyxf(
            'font: italic true; borders: left medium;',
            num_format_str='#,##0.00')
        domain_style_right = xlwt.easyxf(
            'font: italic true; borders: right medium;',
            num_format_str='#,##0.00')
        upper_line_style = xlwt.easyxf(
            'borders: top medium;', num_format_str='#,##0.00')
        def_style = xlwt.easyxf(num_format_str='#,##0.00')

        sheet.col(0).width = 10000

        sheet.write(0, 0, '', title_style)

        x = 1
        for column in self.with_context(is_xls=True).get_columns_names():
            sheet.write(0, x, column, title_style)
            x += 1

        y_offset = 1
        lines = report_id.with_context(
            no_format=True, print_mode=True).get_lines(self)

        for y in range(0, len(lines)):
            if lines[y].get('level') == 0 and lines[y].get('type') == 'line':
                for x in range(0, len(lines[y]['columns']) + 1):
                    sheet.write(y + y_offset, x, None, upper_line_style)
                y_offset += 1
                style_left = level_0_style_left
                style_right = level_0_style_right
                style = level_0_style
            elif lines[y].get('level') == 1 and lines[y].get('type') == 'line':
                for x in range(0, len(lines[y]['columns']) + 1):
                    sheet.write(y + y_offset, x, None, upper_line_style)
                y_offset += 1
                style_left = level_1_style_left
                style_right = level_1_style_right
                style = level_1_style
            elif lines[y].get('level') == 2:
                style_left = level_2_style_left
                style_right = level_2_style_right
                style = level_2_style
            elif lines[y].get('level') == 3:
                style_left = level_3_style_left
                style_right = level_3_style_right
                style = level_3_style
            elif lines[y].get('type') != 'line':
                style_left = domain_style_left
                style_right = domain_style_right
                style = domain_style
            else:
                style = def_style
                style_left = def_style
                style_right = def_style
            sheet.write(y + y_offset, 0, lines[y]['name'], style_left)
            for x in xrange(1, len(lines[y]['columns']) + 1):
                if isinstance(lines[y]['columns'][x - 1], tuple):
                    lines[y]['columns'][x - 1] = lines[y]['columns'][x - 1][0]
                if x < len(lines[y]['columns']):
                    sheet.write(
                        y + y_offset, x, lines[y]['columns'][x - 1], style)
                else:
                    sheet.write(
                        y + y_offset, x, lines[y]['columns'][x - 1],
                        style_right)
            if lines[y]['type'] == 'total' or lines[y].get('level') == 0:
                for x in xrange(0, len(lines[0]['columns']) + 1):
                    sheet.write(y + 1 + y_offset, x, None, upper_line_style)
                y_offset += 1
        if lines:
            for x in xrange(0, len(lines[0]['columns']) + 1):
                sheet.write(len(lines) + y_offset, x, None, upper_line_style)

        book.save(response.stream)

    @api.model
    def return_context(self, report_model, given_context, report_id=None):
        context_model = self._report_model_to_report_context()[report_model]
        domain = [('create_uid', '=', self.env.user.id)]
        if report_id:
            domain.append(('report_id', '=', int(report_id)))
        context = False
        if not context:
            create_vals = {}
            if report_id:
                create_vals['report_id'] = report_id
            context = self.env[context_model].create(create_vals)
        if 'force_account' in given_context:
            context.unfolded_lines = [(6, 0, [given_context['active_id']])]
        update = {}
        for field in given_context:
            if field.startswith('add_'):
                if field.startswith('add_tag_'):
                    ilike = self.env['account.report.tag.ilike'].create({'text': given_context[field]})
                    update[field[8:]] = [(4, ilike.id)]
                else:
                    if field[4:] == 'currency_ids':
                        update[field[4:]] = [(6, 0, [int(given_context[field])])]
                    elif field[4:] == 'currency_payable_ids':
                        update[field[4:]] = [(6, 0, [int(given_context[field])])]
                    else:
                        update[field[4:]] = [(4, int(given_context[field]))]
            if field.startswith('remove_'):
                update[field[7:]] = [(3, int(given_context[field]))]
            if context._fields.get(field) and given_context[field] != 'undefined':
                if given_context[field] == 'false':
                    given_context[field] = False
                if given_context[field] == 'none':
                    given_context[field] = None
                if field in ['filter_product_ids']:
                    update[field] = [(6, 0, [int(id) for id in given_context[field]])]
                else:
                    update[field] = given_context[field]
        if update:
            context.write(update)
        return [context_model, context.id]
