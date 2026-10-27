"""
Shared pieces for every Selenium test, so a change (a new landing page after login, a new port) is fixed ONCE here.

  FRONTEND_URL     one place for the frontend address. Default http://localhost:5173, override with the
                   FRONTEND_URL environment variable.
  BACKEND_API_URL  same for the API (default http://127.0.0.1:8000/api/v1).
  login(...)       logs in and waits until the app has left the login page. It does NOT care where the app
                   lands afterwards (today /dashboard), so a new landing page never breaks the tests again.
  DEMO_USERS       the demo company logins (company "Acme Technologies Ltd."), straight from core/demo.py,
                   created by:  python manage.py seed_demo_data
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _path in (BASE_DIR, os.path.join(BASE_DIR, 'apps')):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from core import demo  # noqa: E402  (plain constants: needs no Django setup)

FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5173').rstrip('/')
BACKEND_API_URL = os.environ.get('BACKEND_API_URL', 'http://127.0.0.1:8000/api/v1').rstrip('/')
WAIT_SECONDS = 15

# The password the self-made test users of the older test files use.
DEFAULT_PASSWORD = 'TestPass123'

DEMO_PASSWORD = demo.PASSWORD
DEMO_USERS = {role: demo.email(local) for role, local in demo.LOGINS}
DEMO_USERS[demo.PLATFORM_LOGIN[0]] = demo.email(demo.PLATFORM_LOGIN[1])

_LOGIN_BUTTON = "//button[normalize-space()='Login' or normalize-space()='Log in']"


def make_driver():
    """A Chrome window and a WebDriverWait for it: (driver, wait). Set HEADLESS=1 to hide the window."""
    from selenium import webdriver
    from selenium.webdriver.support.ui import WebDriverWait
    options = webdriver.ChromeOptions()
    options.add_experimental_option(
        "prefs",
        {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.password_manager_leak_detection": False,
        },
    )
    if os.environ.get('HEADLESS') == '1':
        options.add_argument('--headless=new')
        options.add_argument('--window-size=1440,900')
    driver = webdriver.Chrome(options=options)
    if os.environ.get('HEADLESS') != '1':
        driver.maximize_window()
    return driver, WebDriverWait(driver, WAIT_SECONDS)


def wait_until_signed_in(wait):
    """The app has left the login/register page. Where it went does not matter."""
    wait.until(lambda d: '/login' not in d.current_url and '/register' not in d.current_url)


def login(driver, wait, email, password=DEFAULT_PASSWORD):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    driver.get(f'{FRONTEND_URL}/login')
    email_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
    email_input.clear()
    email_input.send_keys(email)
    password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    password_input.clear()
    password_input.send_keys(password)
    wait.until(EC.element_to_be_clickable((By.XPATH, _LOGIN_BUTTON))).click()
    wait_until_signed_in(wait)


def login_as_demo(driver, wait, role):
    """role: 'CEO', 'Manager', 'HR', 'Accountant', 'Employee' or 'Platform Admin'."""
    login(driver, wait, DEMO_USERS[role], DEMO_PASSWORD)


def open_organization(driver, wait):
    from selenium.webdriver.support import expected_conditions as EC
    driver.get(f'{FRONTEND_URL}/organization')
    wait.until(EC.url_contains('/organization'))


def land_on_organization(driver, wait):
    """For the older tests that were written when login/registration ended on the Organization page."""
    wait_until_signed_in(wait)
    open_organization(driver, wait)


def land_after_registration(driver, wait, subdomain):
    """A new company now lands on the Choose a plan page (ST-147) and its owner cannot work until a first payment is
    approved. These older tests are about something else, so they activate the company directly in the database
    and carry on. (The payment flow itself has its own tests: TC-110 and TC-111.)"""
    wait.until(lambda d: '/subscribe' in d.current_url)
    from billing.models import Subscription
    Subscription.objects.filter(company__subdomain=subdomain).update(status=Subscription.STATUS_ACTIVE)
    land_on_organization(driver, wait)


def clear_session(driver):
    driver.execute_script('window.localStorage.clear();')
    driver.delete_all_cookies()
