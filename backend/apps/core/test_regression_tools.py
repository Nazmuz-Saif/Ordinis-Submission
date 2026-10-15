"""Tests for the regression tooling itself (regression.py, tests/selenium_runner.py, tests/selenium_helpers.py). No browser needed."""
import importlib
import io
import os
import re
import sys
import unittest
from unittest import mock

from django.test import SimpleTestCase

BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TESTS_DIR = os.path.join(BACKEND, 'tests')
for path in (TESTS_DIR, BACKEND):
    if path not in sys.path:
        sys.path.insert(0, path)

import regression  # noqa: E402
import selenium_helpers  # noqa: E402
import selenium_runner  # noqa: E402

try:
    import selenium  # noqa: F401
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

from core import demo  # noqa: E402


def _suite(*names):
    # Built inside a function so Django's own test discovery does not find (and run) these on-purpose failures.
    class Cases(unittest.TestCase):
        def test_tc77_this_one_passes(self):
            pass

        def test_tc78_this_one_fails(self):
            self.fail('made to fail on purpose')

        def test_tc79_this_one_errors(self):
            raise RuntimeError('boom')

        @unittest.skip('not today')
        def test_tc80_this_one_is_skipped(self):
            pass

    suite = unittest.TestSuite()
    for name in names:
        suite.addTest(Cases(name))
    return suite


class FakeDriver:
    current_url = 'http://localhost:5173/dashboard'

    def __init__(self):
        self.calls = []

    def get(self, url):
        self.calls.append(('get', url))

    def find_element(self, by, value=None):
        driver = self

        class Element:
            def send_keys(self, text):
                driver.calls.append(('type', value, text))

            def clear(self):
                pass

            def click(self):
                driver.calls.append(('click', value))

            def is_displayed(self):
                return True

            def is_enabled(self):
                return True
        return Element()


class FakeWait:
    def __init__(self, driver):
        self.driver = driver

    def until(self, condition):
        result = condition(self.driver)
        assert result, 'a wait condition was not met'
        return result


class ReportLinesTests(SimpleTestCase):
    def run_cases(self, *names):
        out = io.StringIO()
        result = selenium_runner.LineResult(out)
        _suite(*names).run(result)
        return out.getvalue(), result

    def test_every_test_case_gets_its_own_pass_or_fail_line(self):
        text, result = self.run_cases('test_tc77_this_one_passes', 'test_tc78_this_one_fails',
                                      'test_tc79_this_one_errors', 'test_tc80_this_one_is_skipped')
        lines = text.strip().splitlines()
        self.assertEqual([l.split()[0] for l in lines], ['PASS', 'FAIL', 'ERROR', 'SKIP'])
        self.assertIn('TC-77', lines[0])
        self.assertIn('TC-78', lines[1])
        self.assertIn('made to fail on purpose', lines[1])
        self.assertIn('boom', lines[2])
        self.assertEqual(len(result.rows), 4)

    def test_the_tc_number_and_story_come_from_the_name(self):
        self.assertEqual(selenium_runner.tc_label('x.Y.test_tc7_abc'), 'TC-07')
        self.assertEqual(selenium_runner.tc_label('x.Y.test_01_abc', 'ST-9 TC-24: text'), 'TC-24')
        self.assertEqual(selenium_runner.tc_label('x.Y.test_01_abc'), '-')
        self.assertEqual(selenium_runner.tc_label('test_st120_tc51_create_edit_salary.Case.test'), 'TC-51', 'number in the file name')
        self.assertEqual(selenium_runner.tc_label('test_st125_selenium.Case.test_tc62_x'), 'TC-62')
        self.assertEqual(selenium_runner.story_label('test_st120_tc51_create_edit_salary'), 'ST-120')
        self.assertEqual(selenium_runner.story_label('test_st125_selenium'), 'ST-125')

    def test_a_tc_number_used_by_two_stories_is_reported(self):
        clash = selenium_runner.duplicate_tc_numbers([('ST-112', 'TC-24'), ('ST-115', 'TC-24'), ('ST-116', 'TC-36'), ('ST-116', '-')])
        self.assertEqual(clash, {'TC-24': ['ST-112', 'ST-115']})


class ExitCodeTests(SimpleTestCase):
    """What TC-76 checks: a failing test case must give a non-zero exit code."""

    def main(self, *names, preflight=True):
        out = io.StringIO()
        with mock.patch.object(selenium_runner, 'load_tests', return_value=_suite(*names)), \
                mock.patch.object(selenium_runner, 'preflight', return_value=preflight), \
                mock.patch.object(selenium_runner, 'ensure_demo_company'):
            code = selenium_runner.main([], out=out)
        return code, out.getvalue()

    def test_all_passing_exits_0(self):
        code, text = self.main('test_tc77_this_one_passes')
        self.assertEqual(code, 0)
        self.assertIn('1 passed, 0 failed', text)

    def test_one_failing_test_exits_1_and_is_listed_at_the_end(self):
        code, text = self.main('test_tc77_this_one_passes', 'test_tc78_this_one_fails')
        self.assertEqual(code, 1)
        self.assertIn('1 passed, 1 failed', text)
        self.assertRegex(text, r'FAIL\s+\S+\s+TC-78')
        self.assertIn('FAIL', text.split('-' * 60)[-1])

    def test_an_error_also_exits_1(self):
        self.assertEqual(self.main('test_tc79_this_one_errors')[0], 1)

    def test_servers_not_running_exits_2_and_runs_nothing(self):
        code, text = self.main('test_tc77_this_one_passes', preflight=False)
        self.assertEqual(code, 2)
        self.assertNotIn('PASS', text)

    def test_the_preflight_names_the_missing_server_and_how_to_start_it(self):
        out = io.StringIO()
        with mock.patch.object(selenium_runner, 'urlopen', side_effect=OSError('refused')):
            self.assertFalse(selenium_runner.preflight(out))
        text = out.getvalue()
        self.assertIn('frontend', text)
        self.assertIn('backend', text)
        self.assertIn('runserver', text)

    def test_an_http_error_answer_counts_as_running(self):
        from urllib.error import HTTPError
        out = io.StringIO()
        error = HTTPError('http://x', 401, 'Unauthorized', {}, None)
        with mock.patch.object(selenium_runner, 'urlopen', side_effect=error):
            self.assertTrue(selenium_runner.preflight(out))

    def test_no_matching_test_exits_2(self):
        out = io.StringIO()
        with mock.patch.object(selenium_runner, 'load_tests', return_value=unittest.TestSuite()):
            self.assertEqual(selenium_runner.main([], out=out), 2)


@unittest.skipUnless(HAS_SELENIUM, 'selenium is not installed')
class RealSuiteTests(SimpleTestCase):
    def test_every_selenium_file_is_found_whatever_its_name(self):
        found = set(selenium_runner.module_names())
        for path in os.listdir(TESTS_DIR):
            if path.startswith('test_') and path.endswith('.py'):
                text = open(os.path.join(TESTS_DIR, path), encoding='utf-8').read()
                if 'unittest' in text and 'webdriver' in text:
                    self.assertIn(path[:-3], found, f'{path} drives a browser but the runner would skip it')
        self.assertIn('test_st124_tc60_ceo_blocked_from_admin', found)
        self.assertNotIn('test_employee_roles', found)

    def test_every_selenium_file_is_found_and_listed(self):
        names = selenium_runner.module_names()
        self.assertGreaterEqual(len(names), 29)
        out = io.StringIO()
        self.assertEqual(selenium_runner.main(['--list'], out=out), 0)
        self.assertRegex(out.getvalue(), r'\d+ test cases in \d+ files')
        self.assertGreaterEqual(len(list(selenium_runner._all_tests(selenium_runner.load_tests()))), 47)

    def test_only_filters_by_story_and_by_tc(self):
        by_story = list(selenium_runner._all_tests(selenium_runner.load_tests(['ST-125'])))
        self.assertTrue(by_story)
        self.assertTrue(all('st125' in t.id() for t in by_story))
        by_tc = list(selenium_runner._all_tests(selenium_runner.load_tests(['TC-62'])))
        self.assertEqual(len(by_tc), 1)


class SharedHelperTests(SimpleTestCase):
    def test_login_types_the_credentials_clicks_login_and_waits_to_leave_the_login_page(self):
        driver = FakeDriver()
        selenium_helpers.login(driver, FakeWait(driver), 'a@b.com', 'Secret123')
        self.assertEqual(driver.calls[0], ('get', f'{selenium_helpers.FRONTEND_URL}/login'))
        self.assertIn(('type', "input[type='email']", 'a@b.com'), driver.calls)
        self.assertIn(('type', "input[type='password']", 'Secret123'), driver.calls)
        self.assertEqual(driver.calls[-1][0], 'click')

    def test_login_does_not_care_where_the_app_lands(self):
        for landing in ('/dashboard', '/organization', '/admin/companies', '/anything-new'):
            driver = FakeDriver()
            driver.current_url = f'http://localhost:5173{landing}'
            selenium_helpers.login(driver, FakeWait(driver), 'a@b.com')

    def test_still_on_the_login_page_is_not_signed_in(self):
        driver = FakeDriver()
        driver.current_url = 'http://localhost:5173/login'
        with self.assertRaises(AssertionError):
            selenium_helpers.wait_until_signed_in(FakeWait(driver))

    def test_the_frontend_address_has_one_default_and_one_override(self):
        with mock.patch.dict(os.environ, {'FRONTEND_URL': ''}, clear=False):
            os.environ.pop('FRONTEND_URL')
            reloaded = importlib.reload(selenium_helpers)
            self.assertEqual(reloaded.FRONTEND_URL, 'http://localhost:5173')
        with mock.patch.dict(os.environ, {'FRONTEND_URL': 'http://localhost:9999/'}):
            self.assertEqual(importlib.reload(selenium_helpers).FRONTEND_URL, 'http://localhost:9999')
        importlib.reload(selenium_helpers)

    def test_the_test_users_are_the_demo_company_logins(self):
        users = selenium_helpers.DEMO_USERS
        self.assertEqual(set(users), {'CEO', 'Manager', 'HR', 'Accountant', 'Employee', 'Platform Admin'})
        self.assertEqual(users['CEO'], demo.email('ceo'))
        self.assertEqual(selenium_helpers.DEMO_PASSWORD, demo.PASSWORD)


class NoCopiesAreLeftTests(SimpleTestCase):
    """The shared helper only helps if the copies do not grow back."""

    def files(self):
        return [os.path.join(TESTS_DIR, n + '.py') for n in selenium_runner.module_names()]

    def test_no_file_has_its_own_frontend_address(self):
        for path in self.files():
            text = open(path, encoding='utf-8').read()
            self.assertIsNone(re.search(r'^(FRONTEND_URL|BACKEND_API_URL)\s*=', text, re.M),
                              f'{os.path.basename(path)} defines its own FRONTEND_URL / BACKEND_API_URL')
            self.assertIn('from selenium_helpers import', text, os.path.basename(path))

    def test_no_file_waits_for_a_fixed_page_after_login(self):
        for path in self.files():
            text = open(path, encoding='utf-8').read()
            self.assertIsNone(
                re.search(r'url_contains\(\s*"/organization"\s*\)', text),
                f'{os.path.basename(path)} waits for /organization after login: use login() or wait_until_signed_in()',
            )

    def test_no_login_method_types_the_form_itself(self):
        import ast
        for path in self.files():
            source = open(path, encoding='utf-8').read()
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.FunctionDef) and node.name.startswith('login'):
                    self.assertNotIn('send_keys', ast.get_source_segment(source, node),
                                     f'{os.path.basename(path)}::{node.name} fills the login form itself: call selenium_helpers.login()')


class RegressionEntryPointTests(SimpleTestCase):
    def test_backend_command_covers_every_app_folder(self):
        labels = regression.app_labels()
        for expected in ('core', 'tenants', 'accounts', 'organization', 'rbac', 'approvals', 'tasks', 'payroll',
                         'attendance', 'dashboard', 'platform_admin', 'notifications'):
            self.assertIn(expected, labels)

    def test_unknown_command_prints_help_and_exits_2(self):
        with mock.patch('builtins.print'):
            self.assertEqual(regression.main(['nonsense']), 2)
            self.assertEqual(regression.main([]), 2)

    def test_selenium_command_hands_over_to_the_runner(self):
        with mock.patch.object(selenium_runner, 'main', return_value=7) as runner:
            self.assertEqual(regression.main(['selenium', '--only', 'ST-1']), 7)
        runner.assert_called_once_with(['--only', 'ST-1'])
