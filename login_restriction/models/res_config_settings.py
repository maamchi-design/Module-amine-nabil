from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    restrict_login_start_hour = fields.Float(
        related='company_id.restrict_login_start_hour',
        readonly=False,
        string='Login Start Hour'
    )
    restrict_login_end_hour = fields.Float(
        related='company_id.restrict_login_end_hour',
        readonly=False,
        string='Login End Hour'
    )
