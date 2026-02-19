from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    restrict_login_start_hour = fields.Float(
        string='Login Start Hour',
        default=8.0,
        help="Working hours start time (e.g., 8.0 = 8:00 AM)"
    )
    restrict_login_end_hour = fields.Float(
        string='Login End Hour',
        default=18.0,
        help="Working hours end time (e.g., 18.0 = 6:00 PM)"
    )
