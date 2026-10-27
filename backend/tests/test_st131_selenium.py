"""
ST-131 Selenium tests: Regression command execution and exit code verification.

  TC-76  Run the single regression command from a clean checkout — expect a pass or fail line
         for every test case, and a non-zero exit code when one test is made to fail.

Needs both servers running.
Run:  cd backend && python tests/test_st131_selenium.py        (HEADLESS=1 hides the window)
"""
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from selenium_helpers import (  # noqa: E402
    BASE_DIR,
    FRONTEND_URL,
    clear_session,
    make_driver,
)

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


class ST131RegressionCommandSeleniumTest(unittest.TestCase):
    def setUp(self):
        self.driver, self.wait = make_driver()

    def tearDown(self):
        try:
            self.driver.get(f'{FRONTEND_URL}/login')
            clear_session(self.driver)
        except Exception:
            pass
        self.driver.quit()

    def test_tc76_regression_command_reports_and_fails_on_error(self):
        """TC-76: Regression command prints pass/fail line per test case and exits non-zero on failure."""
        env = os.environ.copy()
        env['HEADLESS'] = '1'

        # 1. Run regression with a passing test case (TC-81)
        proc_pass = subprocess.run(
            [sys.executable, 'regression.py', 'selenium', '--only', 'TC-81'],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )
        self.assertEqual(
            proc_pass.returncode, 0,
            f'Regression command should exit with 0 when tests pass:\n{proc_pass.stdout}\n{proc_pass.stderr}'
        )
        # Verify single line per test case format: PASS  <Story>  <TC>  <method_name>  (<seconds>s)
        self.assertIn('PASS', proc_pass.stdout)
        self.assertIn('ST-134', proc_pass.stdout)
        self.assertIn('TC-81', proc_pass.stdout)
        self.assertIn('passed, 0 failed', proc_pass.stdout)

        # 2. Verify that when one test is made to fail, the regression command exits with non-zero
        temp_fail_file = os.path.join(TESTS_DIR, 'test_temp_tc76_failing_selenium.py')
        try:
            with open(temp_fail_file, 'w', encoding='utf-8') as f:
                f.write(
                    "import unittest\n"
                    "from selenium_helpers import make_driver\n\n"
                    "class TempFailingTest(unittest.TestCase):\n"
                    "    def test_tc999_intentional_failure(self):\n"
                    "        '''Intentional failure to verify TC-76 exit code and output reporting.'''\n"
                    "        self.assertEqual('actual_value', 'expected_value', 'Forced failure for TC-76 verification')\n"
                )

            proc_fail = subprocess.run(
                [sys.executable, 'regression.py', 'selenium', '--only', 'temp_tc76_failing'],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                env=env,
                timeout=120,
            )
            # Expect non-zero exit code
            self.assertNotEqual(
                proc_fail.returncode, 0,
                f'Regression command must exit with non-zero code on test failure, got: {proc_fail.returncode}'
            )
            self.assertEqual(
                proc_fail.returncode, 1,
                f'Expected exit code 1 on test failure, got: {proc_fail.returncode}'
            )
            # Expect a FAIL line with error details
            self.assertIn('FAIL', proc_fail.stdout)
            self.assertIn('test_tc999_intentional_failure', proc_fail.stdout)
            self.assertIn('AssertionError', proc_fail.stdout)
            self.assertIn('1 failed', proc_fail.stdout)

        finally:
            if os.path.exists(temp_fail_file):
                os.remove(temp_fail_file)


if __name__ == '__main__':
    unittest.main(verbosity=2)
