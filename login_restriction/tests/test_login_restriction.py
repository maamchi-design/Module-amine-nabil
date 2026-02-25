from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessDenied
from unittest.mock import patch
from datetime import datetime
import pytz

class TestLoginRestriction(TransactionCase):

    def setUp(self):
        super(TestLoginRestriction, self).setUp()
        self.company = self.env.company
        self.company.write({
            'restrict_login_start_hour': 8.0,
            'restrict_login_end_hour': 18.0,
        })
        self.test_user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
            'email': 'test@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        # Create associated employee
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'user_id': self.test_user.id,
            'has_login_restriction': True,
        })

    def test_login_no_restriction_flag(self):
        """Test that a user with has_login_restriction=False can login anytime."""
        self.employee.has_login_restriction = False
        tz = pytz.timezone('Africa/Casablanca')
        # 11:00 PM in Casablanca
        mock_now = datetime(2024, 1, 1, 23, 0, 0, tzinfo=tz).astimezone(pytz.utc)
        
        with patch('odoo.addons.login_restriction.models.res_users.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            self.assertTrue(self.test_user.with_user(self.test_user)._check_working_hours())

    def test_login_with_restriction_flag(self):
        """Test that a user with has_login_restriction=True is blocked."""
        self.employee.has_login_restriction = True
        tz = pytz.timezone('Africa/Casablanca')
        # 11:00 PM in Casablanca
        mock_now = datetime(2024, 1, 1, 23, 0, 0, tzinfo=tz).astimezone(pytz.utc)
        
        with patch('odoo.addons.login_restriction.models.res_users.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            self.assertFalse(self.test_user.with_user(self.test_user)._check_working_hours())

    def test_admin_exemption(self):
        """Test that admin is allowed to login anytime."""
        admin_user = self.env.ref('base.user_admin')
        tz = pytz.timezone('Africa/Casablanca')
        # 11:00 PM in Casablanca
        mock_now = datetime(2024, 1, 1, 23, 0, 0, tzinfo=tz).astimezone(pytz.utc)
        
        with patch('odoo.addons.login_restriction.models.res_users.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            # Admin should always return True
            self.assertTrue(admin_user._check_working_hours())
