"""
ST-146 API tests: Billing quotes, pricing discounts, duplicate payment & duplicate approval protection.
(selenium runner includes this test file)

  TC-108  [API] Ask for a quote for 1, 3 and 12 months — expect price times months,
          the 12-month discount, and a 40-month request refused.
  TC-109  [API] Submit the same transaction id twice and approve one submission twice
          — expect the second submission refused and no second invoice or extension.

Needs both servers running.
Run:  cd backend && python tests/test_st146_selenium.py
"""
import decimal
import json
import os
import sys
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TESTS_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, TESTS_DIR)
sys.path.insert(0, os.path.join(BACKEND_DIR, 'apps'))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
import django
django.setup()

from billing.models import Invoice, PaymentSubmission, Subscription  # noqa: E402
from selenium_helpers import (  # noqa: E402
    BACKEND_API_URL,
    DEMO_PASSWORD,
    DEMO_USERS,
)


def api_login(email, password):
    req = urllib.request.Request(
        f"{BACKEND_API_URL}/auth/login/",
        data=json.dumps({"email": email, "password": password}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))["access"]


def api_register_waiting_company(name, subdomain, email, password="StrongPass123", full_name="Waiting Owner"):
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
        data = json.loads(resp.read().decode("utf-8"))
    token = data["data"]["access"]
    # company starts in pending_payment status (ST-147)
    return token, email, password, subdomain


class ST146BillingQuoteAndPaymentAPITest(unittest.TestCase):
    def test_tc108_quote_pricing_discounts_and_range_validation(self):
        """TC-108: Ask quote for 1, 3, 12 months -> price*months, 12-mo discount; 40 months -> refused."""
        ts = int(time.time())
        token, _, _, _ = api_register_waiting_company(f"Quote Co {ts}", f"quote-{ts}", f"ceo.{ts}@quote.test")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Quote 1 month Basic: 1500.00, discount 0.00
        url_1 = f"{BACKEND_API_URL}/billing/quote/?plan=Basic&months=1"
        with urllib.request.urlopen(urllib.request.Request(url_1, headers=headers)) as resp:
            self.assertEqual(resp.status, 200)
            data_1 = json.loads(resp.read().decode("utf-8"))["data"]
        self.assertEqual(decimal.Decimal(str(data_1["amount"])), decimal.Decimal("1500.00"))
        self.assertEqual(decimal.Decimal(str(data_1["discount"])), decimal.Decimal("0.00"))

        # 2. Quote 3 months Basic: 4500.00, discount 0.00
        url_3 = f"{BACKEND_API_URL}/billing/quote/?plan=Basic&months=3"
        with urllib.request.urlopen(urllib.request.Request(url_3, headers=headers)) as resp:
            self.assertEqual(resp.status, 200)
            data_3 = json.loads(resp.read().decode("utf-8"))["data"]
        self.assertEqual(decimal.Decimal(str(data_3["amount"])), decimal.Decimal("4500.00"))
        self.assertEqual(decimal.Decimal(str(data_3["discount"])), decimal.Decimal("0.00"))

        # 3. Quote 12 months Basic: 12 months for the price of 10 -> 15000.00, discount 3000.00 (2 months free)
        url_12 = f"{BACKEND_API_URL}/billing/quote/?plan=Basic&months=12"
        with urllib.request.urlopen(urllib.request.Request(url_12, headers=headers)) as resp:
            self.assertEqual(resp.status, 200)
            data_12 = json.loads(resp.read().decode("utf-8"))["data"]
        self.assertEqual(decimal.Decimal(str(data_12["amount"])), decimal.Decimal("15000.00"))
        self.assertEqual(decimal.Decimal(str(data_12["discount"])), decimal.Decimal("3000.00"))
        self.assertEqual(data_12["free_months"], 2)

        # 4. Quote 40 months -> refused (months out of 1..36)
        url_40 = f"{BACKEND_API_URL}/billing/quote/?plan=Basic&months=40"
        refused = False
        try:
            with urllib.request.urlopen(urllib.request.Request(url_40, headers=headers)) as resp:
                pass
        except urllib.error.HTTPError as err:
            self.assertEqual(err.code, 400)
            err_data = json.loads(err.read().decode("utf-8"))
            self.assertEqual(err_data.get("error", {}).get("code"), "MONTHS_OUT_OF_RANGE")
            refused = True
        self.assertTrue(refused, "Requesting a quote for 40 months must be refused with MONTHS_OUT_OF_RANGE")

    def test_tc109_duplicate_transaction_and_duplicate_approval_protection(self):
        """TC-109: Submit duplicate transaction ID -> refused; approve payment twice -> no duplicate invoice/extension."""
        ts = int(time.time())
        token1, _, _, sub1 = api_register_waiting_company(f"Pay1 Co {ts}", f"p1-{ts}", f"ceo.{ts}@p1.test")
        token2, _, _, sub2 = api_register_waiting_company(f"Pay2 Co {ts}", f"p2-{ts}", f"ceo.{ts}@p2.test")

        tx_id = f"TX{ts}TEST"
        payload = {
            "plan": "Basic",
            "months": 3,
            "method": "bkash",
            "payer_name": "Test Payer",
            "payer_number": "01712345678",
            "transaction_id": tx_id,
            "amount": "4500.00",
        }

        # 1. First submission succeeds
        req1 = urllib.request.Request(
            f"{BACKEND_API_URL}/billing/payments/",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token1}"},
            method="POST",
        )
        with urllib.request.urlopen(req1) as resp:
            self.assertEqual(resp.status, 201)
            payment_data = json.loads(resp.read().decode("utf-8"))
            payment_id = payment_data.get("data", {}).get("id") or payment_data.get("id")

        # 2. Second submission with the same transaction id (from company 2) must be refused
        req2 = urllib.request.Request(
            f"{BACKEND_API_URL}/billing/payments/",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token2}"},
            method="POST",
        )
        duplicate_refused = False
        try:
            with urllib.request.urlopen(req2) as resp:
                pass
        except urllib.error.HTTPError as err:
            self.assertEqual(err.code, 400)
            err_data = json.loads(err.read().decode("utf-8"))
            self.assertEqual(err_data.get("error", {}).get("code"), "PAYMENT_TRANSACTION_USED")
            duplicate_refused = True
        self.assertTrue(duplicate_refused, "Submitting the same transaction ID twice must be refused with PAYMENT_TRANSACTION_USED")

        # 3. Platform Admin approves the first submission
        admin_token = api_login(DEMO_USERS["Platform Admin"], DEMO_PASSWORD)
        admin_headers = {"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"}

        approve_req1 = urllib.request.Request(
            f"{BACKEND_API_URL}/platform-admin/admin/payments/{payment_id}/approve/",
            data=b"{}",
            headers=admin_headers,
            method="POST",
        )
        with urllib.request.urlopen(approve_req1) as resp:
            self.assertEqual(resp.status, 200)

        # Snapshot invoice count and end date
        sub_obj = Subscription.objects.get(company__subdomain=sub1)
        initial_end_date = sub_obj.current_period_end
        invoice_count = Invoice.objects.filter(company__subdomain=sub1).count()
        self.assertEqual(invoice_count, 1, "Exactly one invoice should have been generated on approval")

        # 4. Approve the same submission a second time
        approve_req2 = urllib.request.Request(
            f"{BACKEND_API_URL}/platform-admin/admin/payments/{payment_id}/approve/",
            data=b"{}",
            headers=admin_headers,
            method="POST",
        )
        with urllib.request.urlopen(approve_req2) as resp:
            self.assertEqual(resp.status, 200)
            data2 = json.loads(resp.read().decode("utf-8"))
            self.assertIn("already approved", data2.get("message", "").lower())

        # Verify no duplicate invoice and end date not altered
        sub_obj.refresh_from_db()
        self.assertEqual(sub_obj.current_period_end, initial_end_date, "End date should not be altered by duplicate approval")
        self.assertEqual(
            Invoice.objects.filter(company__subdomain=sub1).count(),
            1,
            "Duplicate approval must NOT generate a second invoice"
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
