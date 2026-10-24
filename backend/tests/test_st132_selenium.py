"""
ST-132 Selenium & Review tests: Documentation and API/SRS sync.

  TC-77  [Review] Compare every endpoint in the SDS API table with the running API
         — expect none missing and none extra.
  TC-78  [Review] Open the SRS requirements traceability table — expect every requirement
         marked Done, Partly or Not built, each with the story that delivered it.

Run:  cd backend && python tests/test_st132_selenium.py        (HEADLESS=1 hides the window)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from selenium_helpers import (  # noqa: E402
    BASE_DIR,
    FRONTEND_URL,
    clear_session,
    make_driver,
)

import django  # noqa: E402
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from core import doccheck, docgen, traceability  # noqa: E402
from core.api_matrix import discover_routes  # noqa: E402

DOCS_DIR = docgen.docs_dir()


class ST132DocsAndTraceabilitySeleniumTest(unittest.TestCase):
    def setUp(self):
        self.driver, self.wait = make_driver()

    def tearDown(self):
        try:
            self.driver.get(f'{FRONTEND_URL}/login')
            clear_session(self.driver)
        except Exception:
            pass
        self.driver.quit()

    def test_tc77_compare_sds_api_table_with_running_api(self):
        """TC-77: Compare every endpoint in the SDS API table with running API -> none missing and none extra."""
        # 1. Check code-level sync: no documentation claims something code lacks
        problems = doccheck.check_dir(DOCS_DIR)
        self.assertEqual(problems, [], f'Documentation discrepancies found:\n' + '\n'.join(problems))

        # 2. Check that every discovered route in the running API is documented in SDS
        sds_path = os.path.join(DOCS_DIR, 'Ordinis_SDS.md')
        self.assertTrue(os.path.exists(sds_path), 'Ordinis_SDS.md not found')
        with open(sds_path, encoding='utf-8') as f:
            sds_text = f.read()

        api_table_path = os.path.join(DOCS_DIR, 'generated', 'api-table.md')
        self.assertTrue(os.path.exists(api_table_path), 'generated/api-table.md not found')
        with open(api_table_path, encoding='utf-8') as f:
            api_table_text = f.read()

        routes = discover_routes()
        self.assertGreater(len(routes), 20, 'Expected at least 20 API routes to be discovered')

        for route in routes:
            path = '/' + route.template.replace('{pk}', '{id}')
            self.assertTrue(
                f'`{path}`' in sds_text or path in sds_text,
                f'API route {path} is missing from SDS API table'
            )
            self.assertTrue(
                path in api_table_text,
                f'API route {path} is missing from generated/api-table.md'
            )

        # 3. Use driver to verify web app answers
        self.driver.get(f'{FRONTEND_URL}/login')
        self.assertIn('login', self.driver.current_url.lower())

    def test_tc78_srs_requirements_traceability_table(self):
        """TC-78: SRS traceability table -> every requirement marked Done, Partly or Not built with delivering story."""
        rows = traceability.rows()
        self.assertGreater(len(rows), 40, 'Traceability matrix should have all FR and NFR requirements')

        valid_statuses = {'Done', 'Partly', 'Not built'}
        for rid, text, priority, status, stories, note in rows:
            self.assertIn(
                status, valid_statuses,
                f'Requirement {rid} ({text}) has invalid status {status}'
            )
            self.assertTrue(
                bool(stories and stories.strip()),
                f'Requirement {rid} ({text}) must have delivering story listed'
            )

        # Verify SRS file contains the generated table
        srs_path = os.path.join(DOCS_DIR, 'Ordinis_SRS.md')
        self.assertTrue(os.path.exists(srs_path), 'Ordinis_SRS.md not found')
        with open(srs_path, encoding='utf-8') as f:
            srs_text = f.read()

        self.assertIn('| Req ID | Requirement | Priority | Status | Delivered by | Note |', srs_text)
        self.assertIn('**Done**', srs_text)

        # Use driver to verify UI accessibility
        self.driver.get(f'{FRONTEND_URL}/login')
        self.assertIn('login', self.driver.current_url.lower())


if __name__ == '__main__':
    unittest.main(verbosity=2)
