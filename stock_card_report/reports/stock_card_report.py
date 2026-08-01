# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockCardView(models.TransientModel):
    _name = "stock.card.view"
    _description = "Stock Card View"
    _order = "date"

    date = fields.Datetime()
    product_id = fields.Many2one(comodel_name="product.product")
    product_qty = fields.Float()
    product_uom_qty = fields.Float()
    product_uom = fields.Many2one(comodel_name="uom.uom")
    reference = fields.Char()
    location_id = fields.Many2one(comodel_name="stock.location")
    location_dest_id = fields.Many2one(comodel_name="stock.location")
    is_initial = fields.Boolean()
    product_in = fields.Float()
    product_out = fields.Float()
    picking_id = fields.Many2one(comodel_name="stock.picking")

    @api.depends("reference", "picking_id.origin")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f"{rec.reference} ({rec.picking_id.origin})"
                if rec.picking_id.origin
                else rec.reference
            )


class StockCardReport(models.TransientModel):
    _name = "report.stock.card.report"
    _description = "Stock Card Report"

    # Filters fields, used for data computation
    date_from = fields.Date()
    date_to = fields.Date()
    product_ids = fields.Many2many(comodel_name="product.product")
    location_id = fields.Many2one(comodel_name="stock.location")
    include_child_locations = fields.Boolean(default=True)

    # Data fields, used to browse report data
    results = fields.Many2many(
        comodel_name="stock.card.view",
        compute="_compute_results",
        help="Use compute fields, so there is nothing store in database",
    )

    def _compute_results(self):
        self.ensure_one()
        date_from = self.date_from or "0001-01-01"
        self.date_to = self.date_to or fields.Date.context_today(self)
        if self.include_child_locations:
            locations = self.env["stock.location"].search(
                [("id", "child_of", [self.location_id.id])]
            )
        else:
            locations = self.location_id
        tz = self.env.user.tz or "UTC"
        self.env["stock.move.line"].flush_model()
        self._cr.execute(
            """
            SELECT ml.date AT TIME ZONE 'UTC' AT TIME ZONE %s AS date,
                ml.product_id, ml.quantity_product_uom AS product_qty,
                ml.quantity AS product_uom_qty,
                ml.product_uom_id AS product_uom, ml.reference,
                ml.location_id, ml.location_dest_id,
                case when ml.location_dest_id in %s
                    then ml.quantity_product_uom end as product_in,
                case when ml.location_id in %s
                    then ml.quantity_product_uom end as product_out,
                case when (ml.date AT TIME ZONE 'UTC' AT TIME ZONE %s)::date < %s
                    then True else False end as is_initial,
                ml.picking_id
            FROM stock_move_line ml
            WHERE (ml.location_id in %s or ml.location_dest_id in %s)
                and ml.state = 'done' and ml.product_id in %s
                and (ml.date AT TIME ZONE 'UTC' AT TIME ZONE %s)::date <= %s
            ORDER BY ml.date, ml.reference
        """,
            (
                tz,
                tuple(locations.ids),
                tuple(locations.ids),
                tz,
                date_from,
                tuple(locations.ids),
                tuple(locations.ids),
                tuple(self.product_ids.ids),
                tz,
                self.date_to,
            ),
        )
        stock_card_results = self._cr.dictfetchall()
        ReportLine = self.env["stock.card.view"]
        self.results = [ReportLine.new(line).id for line in stock_card_results]

    def _get_initial(self, product_line):
        product_input_qty = sum(product_line.mapped("product_in"))
        product_output_qty = sum(product_line.mapped("product_out"))
        return product_input_qty - product_output_qty

    def print_report(self, report_type="qweb"):
        self.ensure_one()
        action = (
            report_type == "xlsx"
            and self.env.ref("stock_card_report.action_stock_card_report_xlsx")
            or self.env.ref("stock_card_report.action_stock_card_report_pdf")
        )
        return action.report_action(self, config=False)

    def _get_html(self):
        result = {}
        rcontext = {}
        report = self.browse(self._context.get("active_id"))
        if report:
            rcontext["o"] = report
            result["html"] = self.env["ir.qweb"]._render(
                "stock_card_report.report_stock_card_report_html", rcontext
            )
        return result

    @api.model
    def get_html(self, given_context=None):
        return self.with_context(**(given_context or {}))._get_html()
