# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Stock Kardex',
    'summary': 'View and create reports',
    'category': 'Accounting',
    'description': """
Accounting Reports
==================
    """,
    'depends': ['account', 'stock'],
    'data': [
        'data/account_financial_report_data.xml',
        'views/report_financial.xml',
        'views/search_template_view.xml',
    ],
    'qweb': [
        'static/src/xml/account_report_template.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}
