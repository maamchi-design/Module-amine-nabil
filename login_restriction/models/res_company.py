from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    def init(self):
        """Ensure columns exist to avoid crashes during module upgrades."""
        created = False
        for column in ['restrict_login_start_hour', 'restrict_login_end_hour']:
            self.env.cr.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'res_company' AND column_name = '{column}'
            """)
            if not self.env.cr.fetchone():
                self.env.cr.execute(f'ALTER TABLE res_company ADD COLUMN {column} FLOAT DEFAULT %s', [8.0 if 'start' in column else 18.0])
                created = True
        if created:
            self.env.cr.commit()
            _logger.info("Manually created missing working hours columns in 'res_company'")
        super(ResCompany, self).init()

    restrict_login_start_hour = fields.Float(
        string='Login Start Hour',
        default=8.0,
        prefetch=False,  # CRITICAL: Prevent Odoo ORM from auto-fetching this during migration
        help="Working hours start time (e.g., 8.0 = 8:00 AM)"
    )
    restrict_login_end_hour = fields.Float(
        string='Login End Hour',
        default=18.0,
        prefetch=False,  # CRITICAL: Prevent Odoo ORM from auto-fetching this during migration
        help="Working hours end time (e.g., 18.0 = 6:00 PM)"
    )
