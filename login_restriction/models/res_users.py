"""
ResUsers - Login Restriction Enforcement Model
================================================

Purpose:
    Extends the 'res.users' model to enforce working hours restrictions on
    user login and active sessions. This is the core security model that
    decides whether a user is allowed to be logged in at the current time.

Fields:
    - has_login_restriction (Boolean):
        Per-user toggle for working hours enforcement.
        Default: True (all non-admin users are restricted by default).
        If False, the user is exempt from time-based restrictions.
        prefetch=False to prevent ORM auto-fetching during migrations.

Methods:
    - _check_working_hours():
        Core security check. Determines if the current server time (converted
        to Africa/Casablanca timezone) falls within the company's allowed
        login window.

        Execution Steps:
            1. Verify this is a single record (ensure_one).
            2. If user is admin (base.group_system) → return True (always allowed).
            3. Open a database savepoint (for robustness during upgrades).
            4. Execute raw SQL joining res_users and res_company to fetch:
               - has_login_restriction (from res_users)
               - restrict_login_start_hour (from res_company)
               - restrict_login_end_hour (from res_company)
            5. If has_login_restriction is False → return True (exempt user).
            6. Convert current UTC time to Africa/Casablanca timezone.
            7. Compare current decimal hour against [start_hour, end_hour).
            8. Return True if within range, False if outside.

        Error Handling:
            - Uses savepoint to prevent transaction poisoning if columns
              are missing (e.g., during fresh install).
            - Catches all exceptions and returns True (fail-open) to avoid
              locking users out during upgrades.

        Called By:
            - ir.http._dispatch() → on every HTTP request.
            - res.users._check_credentials() → at login time.

    - _check_credentials(password, user_agent_env):
        Overrides the standard Odoo authentication method to add a working
        hours check after password validation.

        Execution Steps:
            1. Call super()._check_credentials() to validate password first.
            2. If password is valid, call _check_working_hours() on the user.
            3. If outside working hours → raise AccessDenied with a descriptive
               message including the configured hours.
            4. If within working hours → return normally (login succeeds).

        Called By:
            - Odoo's authentication framework during the login process.

Related Models:
    - res.company: Provides restrict_login_start_hour and restrict_login_end_hour
      fields (fetched via raw SQL JOIN in _check_working_hours).
    - ir.http: Calls _check_working_hours() on every dispatched request.

Related JS:
    - login_warning.js: Client-side mirror of the time check logic, used
      to show warnings and trigger reloads (which ir_http then catches).
"""

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
        prefetch=False,
        help="If checked, this user will only be able to log in during working hours."
    )

    def _check_working_hours(self):
        """Check if the current time is within allowed working hours for the user's company.

        Returns:
            bool: True if access is allowed, False if outside working hours.
        """
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
    def _check_credentials(self, password, user_agent_env=None):
        """Override to restrict login outside working hours.

        Raises:
            AccessDenied: If the user's credentials are correct but the current
                time is outside the configured working hours.
        """
        result = super(ResUsers, self)._check_credentials(password, user_agent_env=user_agent_env)

        # If we reach here, credentials are correct.
        user = self.env.user
        if not user._check_working_hours():
            _logger.warning("Access denied for user %s: Outside working hours.", user.login)
            raise AccessDenied(
                _("Access is restricted to working hours (%s - %s). "
                  "Please try again during working hours.") % (
                    self.env['res.company']._fields['restrict_login_start_hour']
                        .convert_to_export(user.company_id.restrict_login_start_hour, user.company_id),
                    self.env['res.company']._fields['restrict_login_end_hour']
                        .convert_to_export(user.company_id.restrict_login_end_hour, user.company_id)
                )
            )
        return result
