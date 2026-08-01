# Copyright 2026 Jarsa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models


class ReportStockCardReportSummaryXlsx(models.AbstractModel):
    _name = "report.stock_card_report_summary.report_summary_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Stock Card Summary XLSX Report"

    def generate_xlsx_report(self, workbook, data, objects):
        report = objects[0]
        sheet = workbook.add_worksheet(_("Stock Card Summary"))
        bold = workbook.add_format({"bold": True})
        number = workbook.add_format({"num_format": "#,##0.00"})
        sheet.write_row(
            0,
            0,
            [
                _("Date From"),
                str(report.date_from or ""),
                _("Date To"),
                str(report.date_to or ""),
                _("Location"),
                report.location_id.complete_name,
            ],
        )
        headers = [_("Product"), _("Initial"), _("In"), _("Out"), _("Final")]
        sheet.write_row(2, 0, headers, bold)
        sheet.set_column(0, 0, 50)
        sheet.set_column(1, 4, 15)
        for row, line in enumerate(report._get_summary_lines(), start=3):
            sheet.write(row, 0, line["product"].display_name)
            sheet.write_number(row, 1, line["initial"], number)
            sheet.write_number(row, 2, line["product_in"], number)
            sheet.write_number(row, 3, line["product_out"], number)
            sheet.write_number(row, 4, line["final"], number)
