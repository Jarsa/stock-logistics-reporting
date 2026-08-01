# Copyright 2026 Jarsa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockCardReport(models.TransientModel):
    _inherit = "report.stock.card.report"

    def _get_summary_lines(self):
        self.ensure_one()
        # ponytail: results is a compute of new() records; lazy access can
        # return it empty, compute explicitly like the base module does.
        self._compute_results()
        lines = []
        for product in self.product_ids:
            product_lines = self.results.filtered(
                lambda line, product=product: line.product_id == product
            )
            initial = self._get_initial(product_lines.filtered("is_initial"))
            period_lines = product_lines.filtered(lambda line: not line.is_initial)
            product_in = sum(period_lines.mapped("product_in"))
            product_out = sum(period_lines.mapped("product_out"))
            lines.append(
                {
                    "product": product,
                    "initial": initial,
                    "product_in": product_in,
                    "product_out": product_out,
                    "final": initial + product_in - product_out,
                }
            )
        return lines

    def print_report_summary(self, report_type="qweb"):
        self.ensure_one()
        action = (
            report_type == "xlsx"
            and self.env.ref(
                "stock_card_report_summary.action_stock_card_report_summary_xlsx"
            )
            or self.env.ref(
                "stock_card_report_summary.action_stock_card_report_summary_pdf"
            )
        )
        return action.report_action(self, config=False)
