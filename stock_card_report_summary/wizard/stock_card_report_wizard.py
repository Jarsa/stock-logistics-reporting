# Copyright 2026 Jarsa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockCardReportWizard(models.TransientModel):
    _inherit = "stock.card.report.wizard"

    def button_export_summary_pdf(self):
        self.ensure_one()
        return self._export_summary("qweb-pdf")

    def button_export_summary_xlsx(self):
        self.ensure_one()
        return self._export_summary("xlsx")

    def _export_summary(self, report_type):
        model = self.env["report.stock.card.report"]
        report = model.create(self._prepare_stock_card_report())
        return report.print_report_summary(report_type)
