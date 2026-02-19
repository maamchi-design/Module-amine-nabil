from odoo import fields, models

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    has_login_restriction = fields.Boolean(
        string='Has Login Restriction',
        default=True,
        help="If checked, this employee will only be able to log in during working hours."
    )

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    has_login_restriction = fields.Boolean(readonly=True)
