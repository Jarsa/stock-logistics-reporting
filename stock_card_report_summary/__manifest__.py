# Copyright 2026 Jarsa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Stock Card Report Summary",
    "summary": "Stock card report without move details, one line per product.",
    "version": "17.0.1.0.0",
    "category": "Warehouse",
    "website": "https://github.com/OCA/stock-logistics-reporting",
    "author": "Jarsa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["stock_card_report"],
    "data": [
        "reports/stock_card_report_summary.xml",
        "wizard/stock_card_report_wizard_view.xml",
    ],
    "installable": True,
}
