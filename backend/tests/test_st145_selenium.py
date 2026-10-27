"""
ST-145 Selenium tests: Expired subscription restricted mode and daily billing reminder job.

  TC-106  [Selenium] Log in as the CEO of a company whose subscription has expired
          — expect the restricted-mode banner and only the Billing page working; other pages show a clear message.
  TC-107  [Selenium] Run the daily command for a company 7 days before its end
          — expect a billing reminder in the CEO's notifications, and no second reminder when the command runs again.

Needs both servers running.
Run:  cd backend && python tests/test_st145_selenium.py        (HEADLESS=1 hides the window)
"""
import datetime
import json
import os
import sys
import time
import unittest
import urllib.request

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TESTS_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, TESTS_DIR)
sys.path.insert(0, os.path.join(BACKEND_DIR, 'apps'))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
import django
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS = ['*']

from django.core.management import call_command  # noqa: E402
from billing.models import Subscription  # noqa: E402
from notifications.models import Notification  # noqa: E402
from selenium_helpers import (  # noqa: E402
    BACKEND_API_URL,
    FRONTEND_URL,
    clear_session,
    login,
    make_driver,
)

from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402


def api_register_company(name, subdomain, email, password="StrongPass123", full_name="Test Owner"):
    """Register company via real HTTP request to the running backend."""
    req = urllib.request.Request(
        f"{BACKEND_API_URL}/auth/register/",
        data=json.dumps({
            "company_name": name,
            "subdomain": subdomain,
            "ceo_full_name": full_name,
            "ceo_email": email,
            "ceo_password": password,
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


class ST145SubscriptionExpirySeleniumTest(unittest.TestCase):
    def setUp(self):
        self.driver, self.wait = make_driver()

    def tearDown(self):
        try:
            self.driver.get(f'{FRONTEND_URL}/login')
            clear_session(self.driver)
        except Exception:
            pass
        self.driver.quit()

    def test_tc106_expired_subscription_restricted_mode(self):
        """TC-106: CEO of expired company -> restricted banner, pages show clear message, only Billing works."""
        ts = int(time.time())
        company_name = f"Expired Co {ts}"
        subdomain = f"exp-{ts}"
        ceo_email = f"ceo.{ts}@exp.test"
        password = "StrongPass123"

        # Register company via HTTP API
        api_register_company(company_name, subdomain, ceo_email, password=password, full_name="Expired Owner")

        # Mark subscription expired in database
        sub = Subscription.objects.get(company__subdomain=subdomain)
        sub.status = Subscription.STATUS_EXPIRED
        sub.save()

        # Log in as the CEO of the expired company
        login(self.driver, self.wait, ceo_email, password)

        # 1. Check /organization: restricted banner and restricted page message must appear
        self.driver.get(f"{FRONTEND_URL}/organization")
        banner = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='subscription-banner']")))
        self.assertTrue(len(banner.text.strip()) > 0, "Subscription banner should be visible on restricted company")

        restricted_msg = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='restricted-page-message']")))
        self.assertIn("subscription has ended", restricted_msg.text.lower(), "Restricted notice must state subscription has ended")
        self.assertIn("closed until the plan is renewed", restricted_msg.text.lower())

        # 2. Check /settings/billing: Billing page works normally without restricted notice
        self.driver.get(f"{FRONTEND_URL}/settings/billing")
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Billing']")))

        # Restricted message should NOT be present on billing page
        restricted_elems = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='restricted-page-message']")
        self.assertEqual(len(restricted_elems), 0, "Billing page must remain accessible and not blocked by restricted notice")

        # Timeline or plan card must be visible
        billing_content = self.wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR, "[data-testid='timeline-card'], [data-testid='billing-plan-card']"
        )))
        self.assertIsNotNone(billing_content, "Billing page content must be rendered")

    def test_tc107_daily_command_billing_reminder(self):
        """TC-107: Daily command 7 days before end -> reminder in CEO notifications, no duplicate on rerun."""
        ts = int(time.time())
        company_name = f"Remind Co {ts}"
        subdomain = f"rem-{ts}"
        ceo_email = f"ceo.{ts}@remind.test"
        password = "StrongPass123"

        api_register_company(company_name, subdomain, ceo_email, password=password, full_name="Remind Owner")
        sub = Subscription.objects.get(company__subdomain=subdomain)

        # Set end date exactly 7 days from today
        today = datetime.date.today()
        sub.current_period_start = today - datetime.timedelta(days=23)
        sub.current_period_end = today + datetime.timedelta(days=7)
        sub.status = Subscription.STATUS_ACTIVE
        sub.reminders_sent = []
        sub.save()

        # Run the daily command
        call_command('process_subscriptions')

        # Verify a billing reminder notification was created for CEO
        ceo_reminders = Notification.objects.filter(
            recipient__user__email=ceo_email,
            kind=Notification.KIND_BILLING_REMINDER
        )
        self.assertEqual(ceo_reminders.count(), 1, "Exactly one reminder notification should be sent")
        first_reminder = ceo_reminders.first()
        self.assertTrue(
            "7 days" in first_reminder.title or "7 days" in first_reminder.message or "7" in first_reminder.title,
            f"Reminder text should mention 7 days: {first_reminder.title} - {first_reminder.message}"
        )

        # Run command second time - expect idempotent (no duplicate notification)
        call_command('process_subscriptions')
        self.assertEqual(
            Notification.objects.filter(recipient__user__email=ceo_email, kind=Notification.KIND_BILLING_REMINDER).count(),
            1,
            "Re-running the command must not send a duplicate reminder"
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
