"""
ST-153 Selenium tests: Platform Admin dashboard and payment approval.
TC-125: Dashboard company-state, revenue and due metrics.
TC-126: Approving a payment updates pending count and revenue.
"""

import os
import re
import sys
import unittest
import uuid
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "apps"))
sys.path.insert(0, str(BASE_DIR / "tests"))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.development",
)

import django
django.setup()

from django.db.models import Sum
from django.utils import timezone

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from billing.models import Invoice, PaymentSubmission, Subscription
from core import demo
from selenium_helpers import (
    FRONTEND_URL,
    clear_session,
    login_as_demo,
    make_driver,
)
from tenants.models import Company


def number_in(value):
    """Convert displayed currency such as 'BDT 1,500.00' to Decimal."""
    return Decimal(re.sub(r"[^0-9.]", "", value) or "0")


class ST153PlatformDashboardSeleniumTest(unittest.TestCase):
    def setUp(self):
        self.company = Company.objects.get(subdomain=demo.SUBDOMAIN)
        self.subscription = Subscription.objects.get(company=self.company)

        self.original_subscription = {
            "plan_id": self.subscription.plan_id,
            "status": self.subscription.status,
            "current_period_start": self.subscription.current_period_start,
            "current_period_end": self.subscription.current_period_end,
            "next_plan_id": self.subscription.next_plan_id,
            "next_plan_from": self.subscription.next_plan_from,
        }

        self.transaction_id = f"SEL153{uuid.uuid4().hex[:10].upper()}"
        self.original_invoice_ids = set(
            Invoice.objects.filter(company=self.company)
            .values_list("id", flat=True)
        )

        self.driver, self.wait = make_driver()

    def tearDown(self):
        try:
            clear_session(self.driver)
        finally:
            self.driver.quit()

        PaymentSubmission.objects.filter(
            company=self.company,
            transaction_id=self.transaction_id,
        ).delete()

        # Remove only invoices created during this test.
        Invoice.objects.filter(company=self.company).exclude(
            id__in=self.original_invoice_ids
        ).delete()

        Subscription.objects.filter(company=self.company).update(
            **self.original_subscription
        )

    def open_dashboard(self):
        self.driver.get(f"{FRONTEND_URL}/admin/dashboard")
        self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//h1[normalize-space()='Dashboard']")
            )
        )
        self.wait.until(
            lambda driver: len(
                driver.find_elements(
                    By.CSS_SELECTOR,
                    "[data-testid='metric-card']",
                )
            ) >= 10
        )

    def metric_text(self, label):
        cards = self.driver.find_elements(
            By.CSS_SELECTOR,
            "[data-testid='metric-card']",
        )
        for card in cards:
            if card.find_element(By.TAG_NAME, "p").text.strip() == label:
                return card.find_element(
                    By.CSS_SELECTOR,
                    "[data-testid='metric-value']",
                ).text.strip()

        self.fail(f"Dashboard metric not found: {label}")

    def metric_number(self, label):
        return number_in(self.metric_text(label))

    def test_tc125_dashboard_shows_company_states_revenue_and_dues(self):
        login_as_demo(self.driver, self.wait, "Platform Admin")
        self.open_dashboard()

        # Check that all required company-state cards are visible.
        total = int(self.metric_text("Companies"))
        active = int(self.metric_text("Active"))
        restricted = int(self.metric_text("Restricted"))
        suspended = int(self.metric_text("Suspended"))

        self.assertEqual(total, Company.objects.count())
        self.assertEqual(
            total,
            active + restricted + suspended,
            "Company-state cards should account for every company.",
        )

        # Verify revenue and due figures against the invoice records.
        today = timezone.localdate()

        paid = Invoice.objects.filter(status=Invoice.STATUS_PAID)
        this_month = paid.filter(
            paid_on__year=today.year,
            paid_on__month=today.month,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        all_time = paid.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        due = Invoice.objects.filter(
            status=Invoice.STATUS_OPEN
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        self.assertEqual(
            self.metric_number("Revenue this month"),
            this_month,
        )
        self.assertEqual(
            self.metric_number("Revenue all time"),
            all_time,
        )
        self.assertEqual(
            self.metric_number("Due"),
            due,
        )

        self.assertTrue(self.metric_text("Pending payments").isdigit())
        self.assertTrue(self.metric_text("Open tickets").isdigit())

    def test_tc126_approving_payment_updates_dashboard_metrics(self):
        login_as_demo(self.driver, self.wait, "Platform Admin")
        self.open_dashboard()

        pending_before = int(self.metric_text("Pending payments"))
        revenue_before = self.metric_number("Revenue all time")
        monthly_before = self.metric_number("Revenue this month")

        # Create one uniquely identifiable pending payment for the demo company.
        payment = PaymentSubmission.objects.create(
            company=self.company,
            plan=self.subscription.plan,
            months=1,
            amount=Decimal("1500.00"),
            method="bkash",
            payer_name="ST153 Selenium Payer",
            payer_number="01700000000",
            transaction_id=self.transaction_id,
            kind="renewal",
            status=PaymentSubmission.STATUS_PENDING,
        )
        amount = Decimal(str(payment.amount))

        self.open_dashboard()
        self.wait.until(
            lambda driver: self.metric_text("Pending payments")
            == str(pending_before + 1)
        )

        # Open the payment queue and find this exact transaction.
        self.driver.get(f"{FRONTEND_URL}/admin/payments")

        search = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='payments-search']")
            )
        )
        search.send_keys(self.transaction_id)

        self.wait.until(
            lambda driver: any(
                self.transaction_id in row.text
                for row in driver.find_elements(
                    By.CSS_SELECTOR,
                    "[data-testid='payment-row']",
                )
            )
        )

        self.wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "[data-testid='payment-open']")
            )
        ).click()

        self.wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "[data-testid='approve-btn']")
            )
        ).click()

        self.wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "[data-testid='confirm-btn']")
            )
        ).click()

        self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='payments-message']")
            )
        )

        payment.refresh_from_db()
        self.assertEqual(
            payment.status,
            PaymentSubmission.STATUS_APPROVED,
        )

        # Reload the dashboard and wait for the new summary.
        self.open_dashboard()

        self.wait.until(
            lambda driver: self.metric_text("Pending payments")
            == str(pending_before)
        )
        self.wait.until(
            lambda driver: self.metric_number("Revenue all time")
            == revenue_before + amount
        )
        self.wait.until(
            lambda driver: self.metric_number("Revenue this month")
            == monthly_before + amount
        )

        self.assertEqual(
            self.metric_number("Pending payments"),
            pending_before,
        )
        self.assertEqual(
            self.metric_number("Revenue all time"),
            revenue_before + amount,
        )
        self.assertEqual(
            self.metric_number("Revenue this month"),
            monthly_before + amount,
        )


if __name__ == "__main__":
    unittest.main()
