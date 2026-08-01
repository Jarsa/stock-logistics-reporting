# Copyright 2026 Jarsa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import timedelta

from odoo import fields
from odoo.tests import common, tagged


@tagged("post_install", "-at_install")
class TestStockCardReportSummary(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        uom = cls.env.ref("uom.product_uom_unit")
        cls.product = cls.env["product.product"].create(
            {
                "name": "Summary Product",
                "type": "product",
                "uom_id": uom.id,
                "uom_po_id": uom.id,
            }
        )
        cls.location_stock = cls.env.ref("stock.stock_location_stock")
        cls.location_customers = cls.env.ref("stock.stock_location_customers")

    @classmethod
    def _create_done_move(cls, qty, location, location_dest, days_ago=0):
        move = cls.env["stock.move"].create(
            {
                "name": cls.product.name,
                "product_id": cls.product.id,
                "product_uom_qty": qty,
                "product_uom": cls.product.uom_id.id,
                "location_id": location.id,
                "location_dest_id": location_dest.id,
            }
        )
        move._action_confirm()
        move.quantity = qty
        move.picked = True
        move._action_done()
        if days_ago:
            date = fields.Datetime.now() - timedelta(days=days_ago)
            move.move_line_ids.date = date
            move.date = date
        return move

    def test_summary_lines(self):
        self._create_done_move(
            50, self.location_customers, self.location_stock, days_ago=7
        )
        self._create_done_move(100, self.location_customers, self.location_stock)
        self._create_done_move(30, self.location_stock, self.location_customers)
        report = self.env["report.stock.card.report"].create(
            {
                "date_from": fields.Date.context_today(self.env.user)
                - timedelta(days=1),
                "product_ids": [(6, 0, [self.product.id])],
                "location_id": self.location_stock.id,
            }
        )
        lines = report._get_summary_lines()
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertEqual(line["product"], self.product)
        self.assertEqual(line["initial"], 50.0)
        self.assertEqual(line["product_in"], 100.0)
        self.assertEqual(line["product_out"], 30.0)
        self.assertEqual(line["final"], 120.0)

    def test_wizard_summary_export(self):
        self._create_done_move(10, self.location_customers, self.location_stock)
        wizard = self.env["stock.card.report.wizard"].create(
            {
                "product_ids": [(6, 0, [self.product.id])],
                "location_id": self.location_stock.id,
            }
        )
        action_pdf = wizard.button_export_summary_pdf()
        self.assertEqual(
            action_pdf["report_name"],
            "stock_card_report_summary.report_stock_card_report_summary_pdf",
        )
        action_xlsx = wizard.button_export_summary_xlsx()
        self.assertEqual(
            action_xlsx["report_name"],
            "stock_card_report_summary.report_summary_xlsx",
        )

    def test_render_reports(self):
        self._create_done_move(10, self.location_customers, self.location_stock)
        report = self.env["report.stock.card.report"].create(
            {
                "product_ids": [(6, 0, [self.product.id])],
                "location_id": self.location_stock.id,
            }
        )
        action = self.env.ref(
            "stock_card_report_summary.action_stock_card_report_summary_pdf"
        )
        html = action._render_qweb_html(action.report_name, report.ids)[0]
        self.assertIn(b"Summary Product", html)
        action_xlsx = self.env.ref(
            "stock_card_report_summary.action_stock_card_report_summary_xlsx"
        )
        content, content_type = action_xlsx._render_xlsx(
            action_xlsx.report_name, report.ids, data={"report_type": "xlsx"}
        )
        self.assertEqual(content_type, "xlsx")
        self.assertTrue(content)
