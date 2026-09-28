from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase
from unittest.mock import patch

from config.settings import get_secret_key


class SecuritySettingsTests(SimpleTestCase):
    def test_browser_security_defaults_are_explicit(self):
        self.assertIs(settings.SESSION_COOKIE_HTTPONLY, True)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, "Lax")
        self.assertEqual(settings.CSRF_COOKIE_SAMESITE, "Lax")
        self.assertEqual(settings.X_FRAME_OPTIONS, "DENY")
        self.assertIs(settings.SECURE_CONTENT_TYPE_NOSNIFF, True)
        self.assertEqual(settings.SECURE_REFERRER_POLICY, "same-origin")

    def test_local_http_keeps_secure_cookies_disabled_by_default(self):
        self.assertIs(settings.SESSION_COOKIE_SECURE, False)
        self.assertIs(settings.CSRF_COOKIE_SECURE, False)

    def test_production_requires_explicit_secret_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ImproperlyConfigured):
                get_secret_key(debug=False)
