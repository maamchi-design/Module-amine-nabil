"""
ResCompany - Working Hours Configuration Model
================================================

Purpose:
    Extends the 'res.company' model to add configurable working hours fields.
    These fields define the allowed login window for non-admin users belonging
    to this company.

Fields:
    - restrict_login_start_hour (Float):
        The start of the allowed login window, expressed as a decimal hour.
        Default: 8.0 (08:00 AM). Example: 9.5 = 09:30 AM.
        Used by: res.users._check_working_hours(), login_warning.js.

    - restrict_login_end_hour (Float):
        The end of the allowed login window, expressed as a decimal hour.
        Default: 18.0 (06:00 PM). Example: 17.25 = 05:15 PM.
        Used by: res.users._check_working_hours(), login_warning.js.

Methods:
    - init():
        Robustness method executed at module loading time. Uses raw SQL to check
        if the 'restrict_login_start_hour' and 'restrict_login_end_hour' columns
        exist in the 'res_company' database table. If missing (e.g., during a
        fresh install or upgrade), it creates them with default values to prevent
        ORM crashes before the schema is fully synchronized.

Related Models:
    - res.users: Reads these fields via raw SQL in _check_working_hours() to
      determine if the current time falls within the allowed window.
    - ir.http: Indirectly uses these values through res.users._check_working_hours()
      on every HTTP request to enforce session logout.

Related JS:
    - login_warning.js: Fetches these fields via RPC to perform client-side
      time checks and display a 5-minute warning before the end hour.
"""

from odoo import fields, models
import logging

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    def init(self):
        """Ensure working hours columns exist to avoid ORM crashes during module upgrades.

        Execution Steps:
            1. For each column ('restrict_login_start_hour', 'restrict_login_end_hour'):
               a. Query information_schema.columns to check if the column exists.
               b. If missing, execute ALTER TABLE to add the column with a default value.
            2. If any column was created, commit the transaction immediately so all
               sessions can see the new schema.
            3. Call super().init() to continue the standard Odoo initialization.
        """
        created = False
        for column in ['restrict_login_start_hour', 'restrict_login_end_hour']:
            self.env.cr.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'res_company' AND column_name = '{column}'
            """)
            if not self.env.cr.fetchone():
                self.env.cr.execute(
                    f'ALTER TABLE res_company ADD COLUMN {column} FLOAT DEFAULT %s',
                    [8.0 if 'start' in column else 18.0]
                )
                created = True
        if created:
            self.env.cr.commit()
            _logger.info("Manually created missing working hours columns in 'res_company'")
        super(ResCompany, self).init()

    restrict_login_start_hour = fields.Float(
        string='Login Start Hour',
        default=8.0,
        prefetch=False,
        help="Working hours start time (e.g., 8.0 = 8:00 AM)"
    )
    restrict_login_end_hour = fields.Float(
        string='Login End Hour',
        default=18.0,
        prefetch=False,
        help="Working hours end time (e.g., 18.0 = 6:00 PM)"
    )
