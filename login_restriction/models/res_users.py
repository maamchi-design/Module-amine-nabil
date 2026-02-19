from odoo import models, api, _
from odoo.exceptions import AccessDenied
import pytz
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _inherit = 'res.users'

    def _check_working_hours(self):
        """Check if the current time is within working hours for the company."""
        self.ensure_one()
        if self._is_admin():
            return True

        # Modification #1: Check the employee-level restriction flag
        # Use raw SQL to avoid ORM UndefinedColumn error if the column is missing in DB but present in registry
        try:
            self.env.cr.execute("""
                SELECT has_login_restriction 
                FROM hr_employee 
                WHERE user_id = %s 
                LIMIT 1
            """, [self.id])
            res = self.env.cr.dictfetchone()
            # If no employee or no flag, we default to restriction for non-admins
            # But during upgrade, if the query fails, we return True (no restriction) to avoid crashes
            if res and not res.get('has_login_restriction', True):
                return True
        except Exception:
            # Column doesn't exist yet or other DB error during migration
            self.env.cr.rollback()
            return True

        company = self.company_id
        tz = pytz.timezone('Africa/Casablanca')
        now_utc = datetime.now(pytz.utc)
        now_local = now_utc.astimezone(tz)
        
        current_hour = now_local.hour + now_local.minute / 60.0
        
        start_hour = company.restrict_login_start_hour
        end_hour = company.restrict_login_end_hour
        
        if not (start_hour <= current_hour < end_hour):
            return False
        return True

    @api.model
    def _check_credentials(self, password, user_agent_env=None):
        """Override to restrict login outside working hours."""
        result = super(ResUsers, self)._check_credentials(password, user_agent_env=user_agent_env)
        
        # If we reach here, credentials are correct.
        user = self.env.user
        if not user._check_working_hours():
            _logger.warning("Access denied for user %s: Outside working hours.", user.login)
            raise AccessDenied(_("Access is restricted to working hours (8:00 AM - 6:00 PM). Please try again during working hours."))
        return result
