# -*- coding: utf-8 -*-
# Copyright 2016, Jarsa Sistemas, S.A. de C.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Stock Kardex',
    'summary': 'View and create reports',
    'category': 'Stock',
    'description': """
Stock Reports
====================
    """,
    'depends': ['stock'],
    'data': [
        'views/kardex_manager_report.xml',
        'data/kardex_general_report_data.xml',
        'views/res_config_settings_view.xml',
    ],
    'qweb': [
        'static/src/xml/kardex_report_backend.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}
