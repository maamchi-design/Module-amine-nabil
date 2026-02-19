from odoo import models
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _dispatch(cls, endpoint):
        """Override to check working hours on every request."""
        if request.session.uid:
            try:
                user = request.env['res.users'].sudo().browse(request.session.uid)
                # We use sudo() to check working hours even if the user has limited access
                if user.active and not user._check_working_hours():
                    _logger.info("Auto-logging out user %s: Working hours ended.", user.login)
                    request.session.logout()
            except Exception:
                # Fallback to allow request if there's a DB/Registry error (e.g. during install)
                pass
        
        return super(IrHttp, cls)._dispatch(endpoint)
