"""
IrHttp - Real-Time Request Interceptor for Working Hours Enforcement
=====================================================================

Purpose:
    Extends the 'ir.http' abstract model to intercept every single HTTP request
    made by authenticated users. This is the primary, real-time enforcement
    layer that ensures no user can remain logged in outside their allowed
    working hours. It acts as a server-side gatekeeper with zero delay.

Methods:
    - _dispatch(endpoint):
        Overrides Odoo's core HTTP dispatch method. This method is called on
        EVERY request (page load, RPC call, button click, etc.).

        Execution Steps:
            1. Check if the current request has an authenticated session
               (request.session.uid is set).
            2. If authenticated, open a database savepoint (for robustness).
            3. Browse the res.users record for the session user (with sudo).
            4. Call user._check_working_hours() to verify if the current
               time is within the allowed window.
            5. If the user is active AND outside working hours:
               a. Log the event: "Auto-logging out user X: Working hours ended."
               b. Call request.session.logout() to destroy the session.
               c. The user will be redirected to the login page.
            6. If the user is within hours (or is admin): proceed normally.
            7. Call super()._dispatch(endpoint) to continue the standard
               Odoo request pipeline.

        Error Handling:
            - Wrapped in try/except with a savepoint to prevent transaction
              poisoning during module installs, upgrades, or registry rebuilds.
            - If any exception occurs (missing columns, registry mismatch),
              the request proceeds normally (fail-open).

Related Models:
    - res.users: Calls _check_working_hours() which reads has_login_restriction
      from res_users and restrict_login_start/end_hour from res_company via
      raw SQL.
    - res.company: Indirectly accessed through res.users._check_working_hours()
      for the configured working hours.

Related JS:
    - login_warning.js: Client-side component that triggers browser.location.reload()
      when the end hour is reached. This reload is what causes _dispatch() to
      execute the logout, creating a seamless enforcement loop.
"""

from odoo import models
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _dispatch(cls, endpoint):
        """Intercept every HTTP request to enforce working hours logout.

        Args:
            endpoint: The Odoo endpoint being dispatched to.

        Returns:
            The result of the standard Odoo dispatch pipeline.
        """
        if request.session.uid:
            try:
                # Wrap in savepoint to prevent transaction abort if checks fail
                with request.env.cr.savepoint():
                    user = request.env['res.users'].sudo().browse(request.session.uid)
                    if user.active and not user._check_working_hours():
                        _logger.info("Auto-logging out user %s: Working hours ended.", user.login)
                        request.session.logout()
            except Exception:
                # Fallback to allow request if there's a DB/Registry error
                pass

        return super(IrHttp, cls)._dispatch(endpoint)
