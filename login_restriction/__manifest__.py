{
    'name': 'Login Access Restriction',
    'version': '17.0.1.0.1',
    'category': 'Extra Tools',
    'summary': 'Restrict login access to working hours (8 AM - 6 PM)',
    'description': """
This module restricts login access for normal users to working hours.
- Configurable working hours per company.
- Administrators are exempt from restrictions.
- 5-minute warning before automatic logout.
- Logs failed login attempts outside working hours.
""",
    'author': 'Antigravity',
    'depends': ['base', 'web', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/hr_employee_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'login_restriction/static/src/js/login_warning.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
