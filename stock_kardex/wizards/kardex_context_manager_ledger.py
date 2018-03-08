# -*- coding: utf-8 -*-
# Copyright 2016, Jarsa Sistemas, S.A. de C.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models


class kardex_context_general_ledger(models.TransientModel):
    _name = "kardex.context.manager.ledger"
    _description = "A particular context for the general ledger"
    _inherit = "kardex.report.context.common"

    fold_field = 'unfolded_lines'
    unfolded_lines = fields.Many2many(
        'product.product',
        'context_to_product_product',
        string='Unfolded Lines')
    date_filter = fields.Char('Date filter used', default=None)
    filter_product_ids = fields.Many2many('product.product')

    def get_report_obj(self):
        return self.env['kardex.manager.ledger']

    @api.multi
    def get_columns_names(self):
        return ['', _("Type"), _("Date"), _("Quantity"),
                _("UoM"), _("Balance"), ]

    @api.multi
    def get_columns_types(self):
        types = []
        limit = len(self.get_columns_names())
        for x in range(limit):
            types.append("text")
        return types

    def get_available_filter_product_ids_names(self):
        return [[a.id, a.code, a.name] for a in self.env['product.product'].search([])]
