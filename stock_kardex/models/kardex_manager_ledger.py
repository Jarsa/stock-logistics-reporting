# -*- coding: utf-8 -*-
# Copyright 2016, Jarsa Sistemas, S.A. de C.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from __future__ import division
from odoo import _, api, models
from odoo.tools.misc import formatLang
from odoo.exceptions import ValidationError
from datetime import datetime
import calendar


class KardexManagerLedger(models.AbstractModel):
    _name = "kardex.manager.ledger"
    _description = "Stock Manager Report"

    @api.model
    def get_date_start(self):
        today = datetime.now()
        month = today.month
        date_string = "%s-%s-01"
        if month < 10:
            date_string = "%s-0%s-01"
        month_start = date_string % (today.year, month)
        return month_start

    @api.model
    def get_date_end(self):
        today = datetime.now()
        month = today.month
        date_string = "%s-%s-%s"
        if month < 10:
            date_string = "%s-0%s-%s"
        month_end = date_string % (
            today.year, today.month, calendar.monthrange(
                today.year - 1, month)[1])
        return month_end

    @api.model
    def _do_query(self, line_id=False):
        pp_obj = self.env['product.product']
        uom_obj = self.env['product.uom']
        sp_obj = self.env['stock.picking']
        results = {}
        context = self.env.context
        tz = self._context.get('tz', 'America/Mexico_City')
        location_id = self.env.user.company_id.location_id.id
        filter_product_ids = context.get('filter_product_ids').ids
        if not location_id:
            raise ValidationError(
                _("Verify that a main warehouse is"
                  " configured for the report."))
        select = (
            """SELECT sm.product_id, sm.name, sm.product_uom_qty,
            sm.picking_id as picking_id,
            sm.date AT TIME ZONE 'UTC' AT TIME ZONE %s AS date,
            sm.id, sm.location_id, sm.location_dest_id, sm.state,
            sm.product_uom
            FROM stock_move sm
            WHERE sm.state = 'done' AND (
                sm.location_id = %s OR sm.location_dest_id = %s)
                AND sm.date AT TIME ZONE 'UTC' AT TIME ZONE %s >= %s
                AND sm.date AT TIME ZONE 'UTC' AT TIME ZONE %s <= %s
            """)
        if line_id:
            select += 'AND sm.product_id = %s' % line_id
        elif filter_product_ids and len(
                filter_product_ids) > 1:
            select += 'AND sm.product_id IN %s' % (tuple(
                filter_product_ids), )
        elif filter_product_ids and len(
                filter_product_ids) == 1:
            select += 'AND sm.product_id = %s' % filter_product_ids[0]
        select += ' ORDER BY sm.date'
        if not context['date_from'] or not context['date_to']:
            context = dict(context)
            context['date_from'] = self.get_date_start()
            context['date_to'] = self.get_date_end()
        start_date = context['date_from'] + ' 00:00:01'
        end_date = context['date_to'] + ' 23:59:59'
        self.env.cr.execute(
            select,
            (tz, location_id, location_id, tz, start_date, tz, end_date))
        query_data = self.env.cr.dictfetchall()
        for item in query_data:
            product = pp_obj.browse(item['product_id'])
            uom_id = uom_obj.browse(item['product_uom'])
            product_uom_qty = uom_id._compute_quantity(
                item['product_uom_qty'], product.uom_id)
            if item['product_id'] not in results.keys():
                results[item['product_id']] = []
            results[item['product_id']].append({
                'location_id': item['location_id'],
                'location_dest_id': item['location_dest_id'],
                'product_uom_qty': (
                    product_uom_qty if item['location_dest_id'] ==
                    location_id
                    else -product_uom_qty),
                'date': item['date'],
                'move_id': item['id'],
                'move_name': (item['name'] if item['picking_id'] is None
                              else sp_obj.browse(item['picking_id']).name),
                'picking_id': item['picking_id'],
                'product_uom': item['product_uom'],
            })
        return results

    def get_lines(self, context_id, line_id=None):
        if isinstance(context_id, int):
            context_id = self.env['kardex.context.manager.ledger'].search(
                [('id', '=', context_id)])
        new_context = dict(self._context)
        new_context.update({
            'date_from': context_id.date_from,
            'date_to': context_id.date_to,
            'context_id': context_id,
            'filter_product_ids': context_id.filter_product_ids,
        })
        return self.with_context(new_context)._lines(line_id)

    @api.model
    def get_initial_balance(self, product_id, date_from, location_id):
        total_out = 0.0
        total_in = 0.0
        moves_out = self.env['stock.move'].read_group(
            [('product_id', '=', product_id),
             ('location_id', '=', location_id),
             ('date', '<=', date_from), ('state', '=', 'done')],
            ['product_id', 'product_qty'],
            ['product_id'])
        moves_in = self.env['stock.move'].read_group(
            [('product_id', '=', product_id),
             ('location_dest_id', '=', location_id),
             ('date', '<=', date_from), ('state', '=', 'done')],
            ['product_id', 'product_qty'],
            ['product_id'])
        if moves_out:
            total_out = moves_out[0]['product_qty']
        if moves_in:
            total_in = moves_in[0]['product_qty']
        return total_in - total_out

    @api.model
    def _lines(self, line_id=None):
        lines = []
        uom_obj = self.env['product.uom']
        location = self.env.user.company_id.location_id.id
        if not location:
            raise ValidationError(
                _("Verify that a main warehouse is"
                  " configured for the report."))
        product_obj = self.env['product.product']
        stock_location_obj = self.env['stock.location']
        context = self.env.context
        line_id = line_id or None
        data = self._do_query(line_id)
        unfold_all = (
            context.get('print_mode') and not
            context['context_id']['unfolded_lines'])
        for product_id, moves in data.items():
            domain_lines = []
            product = product_obj.browse(product_id)
            balance = 0
            date_from_str = context['date_from']
            balance = self.get_initial_balance(
                product_id, date_from_str, location)
            lines.append({
                'id': product_id,
                'type': 'line',
                'name': product.name,
                'columns': (
                    [product.uom_id.name,
                     sum([x['product_uom_qty'] for x in moves]) + balance]),
                'level': 2,
                'unfoldable': True,
                'unfolded': (
                    product_id in
                    context['context_id']['unfolded_lines'].ids or
                    unfold_all),
                'footnotes': {},
                'colspan': 5,
            })
            if (product_id in context['context_id']['unfolded_lines'].ids or
                    unfold_all):
                domain_lines = [{
                    'id': product_id,
                    'type': 'initial_balance',
                    'name': _('Initial Balance'),
                    'columns': ['', '', '', '', '', balance],
                    'footnotes': {},
                    'level': 1,
                }]
                for line in moves:
                    product_uom = uom_obj.browse(line['product_uom']).name
                    location_id = stock_location_obj.browse(
                        line['location_id'])
                    location_dest_id = stock_location_obj.browse(
                        line['location_dest_id'])
                    balance += line['product_uom_qty']
                    line_value = {
                        'id': line['move_id'],
                        'type': 'move_line_id',
                        'move_id': (
                            line['picking_id'] if line['picking_id'] is not
                            None else False),
                        'name': line['move_name'],
                        'columns': [
                            '', 'IN <-- %s' % location_id.name if
                            line['location_dest_id'] == location
                            else 'OUT --> %s' %
                            location_dest_id.name, line['date'], line[
                                'product_uom_qty'], product_uom, balance],
                        'footnotes': {},
                        'level': 1,
                    }
                    import ipdb; ipdb.set_trace()
                    domain_lines.append(line_value)
                lines += domain_lines
        return lines

    @api.model
    def get_title(self):
        return _("Stock Kardex")

    @api.model
    def get_name(self):
        return 'manager_ledger'

    @api.model
    def get_report_type(self):
        return 'date_range'

    def get_template(self):
        return 'stock_kardex.main_kardex_general_report'
