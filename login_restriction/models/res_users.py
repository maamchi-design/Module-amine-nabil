from odoo import models, fields, api, _
from odoo.exceptions import AccessDenied
import pytz
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _inherit = 'res.users'

    has_login_restriction = fields.Boolean(
        string='Has Login Restriction',
        default=True,
        prefetch=False,  # CRITICAL: Prevent Odoo ORM from auto-fetching this during migration
        help="If checked, this user will only be able to log in during working hours."
    )

    def _check_working_hours(self):
        """Check if the current time is within working hours for the company."""
        self.ensure_one()
        if self._is_admin():
            return True

        # Defensive check using raw SQL and savepoint to avoid poisoned transactions
        # during module upgrades/installs when columns might be missing from DB.
        try:
            with self.env.cr.savepoint():
                self.env.cr.execute("""
                    SELECT u.has_login_restriction, 
                           c.restrict_login_start_hour, 
                           c.restrict_login_end_hour
                    FROM res_users u
                    JOIN res_company c ON u.company_id = c.id
                    WHERE u.id = %s
                """, [self.id])
                res = self.env.cr.dictfetchone()
                
                if not res or not res.get('has_login_restriction', True):
                    return True

                start_hour = res.get('restrict_login_start_hour', 8.0)
                end_hour = res.get('restrict_login_end_hour', 18.0)
        except Exception:
            # If query fails (e.g. column missing), we bypass restriction safely
            return True

        tz = pytz.timezone('Africa/Casablanca')
        now_utc = datetime.now(pytz.utc)
        now_local = now_utc.astimezone(tz)
        
        current_hour = now_local.hour + now_local.minute / 60.0
        
        if not (start_hour <= current_hour < end_hour):
            return False
        return True

    @api.model
    def _cron_enforce_login_restrictions(self):
        """CRON method to identify and force logout users outside working hours."""
        restricted_users = self.search([
            ('has_login_restriction', '=', True),
            ('active', '=', True)
        ])
        
        users_to_logout = []
        for user in restricted_users:
            if not user._check_working_hours():
                users_to_logout.append(user)
                _logger.info("CRON: Identifying user %s for forced logout (outside working hours).", user.login)

        if users_to_logout:
            # Send a bus notification to force reload/logout for these users
            # This works if the users have an active web session
            bus_bus = self.env['bus.bus']
            for user in users_to_logout:
                # We use a custom 'login_restriction_logout' message
                bus_bus._sendone(user.partner_id, 'login_restriction_logout', {
                    'message': _("Your working hours have ended. You will be logged out."),
                })
        return True

    @api.model
    def _check_credentials(self, password, user_agent_env=None):
        """Override to restrict login outside working hours."""
        result = super(ResUsers, self)._check_credentials(password, user_agent_env=user_agent_env)
        
        # If we reach here, credentials are correct.
        user = self.env.user
        if not user._check_working_hours():
            _logger.warning("Access denied for user %s: Outside working hours.", user.login)
            raise AccessDenied(_("Access is restricted to working hours (%s - %s). Please try again during working hours.") % (
                self.env['res.company']._fields['restrict_login_start_hour'].convert_to_export(user.company_id.restrict_login_start_hour, user.company_id),
                self.env['res.company']._fields['restrict_login_end_hour'].convert_to_export(user.company_id.restrict_login_end_hour, user.company_id)
            ))
        return result
