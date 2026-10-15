"""
One command that runs EVERY Selenium test case and prints PASS / FAIL for each.

    python regression.py selenium                 all test cases
    python regression.py selenium --only ST-125   one story        (also: --only TC-24, --only leave)
    python regression.py selenium --list          show what would run, run nothing
    python regression.py selenium --fresh-demo    rebuild the demo company first (seed_demo_data --reset)

Before it starts it checks that the backend and the frontend answer, and makes sure the demo company exists
(seed_demo_data never deletes anything). Exit code: 0 all passed, 1 something failed, 2 could not start.
"""
import argparse
import glob
import importlib
import io
import os
import re
import sys
import time
import unittest
from collections import defaultdict
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(TESTS_DIR)
for _path in (TESTS_DIR, BASE_DIR, os.path.join(BASE_DIR, 'apps')):
    if _path not in sys.path:
        sys.path.insert(0, _path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import selenium_helpers as helpers  # noqa: E402

def module_names():
    """Every test file in tests/ that drives a browser. Found by what is inside, not by what it is called."""
    names = []
    for path in sorted(glob.glob(os.path.join(TESTS_DIR, 'test_*.py'))):
        with open(path, encoding='utf-8') as handle:
            text = handle.read()
        if 'unittest' in text and 'selenium' in text:   # the old test_employee_roles.py is a plain function: skipped
            names.append(os.path.splitext(os.path.basename(path))[0])
    return names


def tc_label(test_id, doc=''):
    """TC number from the method name (test_tc62_...), the file name (test_st120_tc51_...) or the docstring."""
    match = re.search(r'(?:^|[._])tc(\d+)(?:_|$)', test_id) or re.search(r'TC-(\d+)', doc or '')
    return f'TC-{int(match.group(1)):02d}' if match else '-'


def story_label(module):
    match = re.search(r'_st(\d+)(?:_|$)', module)
    return f'ST-{match.group(1)}' if match else module.replace('test_', '').replace('_selenium', '')[:18]


class LineResult(unittest.TestResult):
    """Prints one line per test case the moment it finishes."""

    def __init__(self, out):
        super().__init__()
        self.out = out
        self.rows = []     # (status, story, tc, name, seconds, note)
        self._started = {}

    def startTest(self, test):
        super().startTest(test)
        self._started[test.id()] = time.time()

    def _row(self, status, test, note=''):
        test_id = test.id()
        parts = test_id.split('.')
        module, name = parts[0], parts[-1]
        if name.startswith('setUpClass') or ' ' in test_id:
            module = re.sub(r'.*\((?:.*\.)?([^.)]+)\.[^.)]+\)', r'\1', test_id) or module
        doc = getattr(getattr(test, '_testMethodName', None) and getattr(test, test._testMethodName, None), '__doc__', '') or ''
        seconds = time.time() - self._started.get(test_id, time.time())
        row = (status, story_label(module), tc_label(test_id, doc), name, seconds, note)
        self.rows.append(row)
        note_text = f'  <- {note}' if note else ''
        self.out.write(f'{status:<5} {row[1]:<10} {row[2]:<6} {name}  ({seconds:.1f}s){note_text}\n')
        self.out.flush()

    @staticmethod
    def _first_line(err):
        text = ''.join(__import__('traceback').format_exception_only(err[0], err[1])).strip()
        return text.splitlines()[0][:160] if text else ''

    def addSuccess(self, test):
        super().addSuccess(test)
        self._row('PASS', test)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._row('FAIL', test, self._first_line(err))

    def addError(self, test, err):
        super().addError(test, err)
        self._row('ERROR', test, self._first_line(err))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._row('SKIP', test, reason)


def load_tests(only=None, names=None):
    suite = unittest.TestSuite()
    loader = unittest.defaultTestLoader
    wanted = [o.lower() for o in (only or [])]
    for name in names or module_names():
        module = importlib.import_module(name)
        for group in loader.loadTestsFromModule(module):
            for test in group:
                doc = getattr(getattr(test, test._testMethodName, None), '__doc__', '') or ''
                keys = f'{story_label(name)} {tc_label(test.id(), doc)} {test.id()}'.lower()
                if not wanted or any(w in keys for w in wanted):
                    suite.addTest(test)
    return suite


def _all_tests(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _all_tests(item)
        else:
            yield item


def duplicate_tc_numbers(rows_or_tests):
    """TC numbers used in more than one test file (a numbering clash worth fixing)."""
    seen = defaultdict(set)
    for story, tc in rows_or_tests:
        if tc != '-':
            seen[tc].add(story)
    return {tc: sorted(stories) for tc, stories in seen.items() if len(stories) > 1}


def preflight(out):
    """The backend and the frontend must answer. Returns True when both do."""
    ok = True
    checks = [('frontend', helpers.FRONTEND_URL, 'npm run dev    (in the frontend folder)'),
              ('backend', helpers.BACKEND_API_URL + '/auth/me/', 'python manage.py runserver    (in the backend folder)')]
    for label, url, how in checks:
        try:
            urlopen(url, timeout=5)
        except HTTPError:
            pass   # any HTTP answer (the API answers 401 without a login) means it is running
        except (URLError, OSError):
            ok = False
            out.write(f'NOT RUNNING: the {label} does not answer at {url}\n  start it with: {how}\n')
    return ok


def ensure_demo_company(out, fresh):
    import django
    django.setup()
    from django.core.management import call_command
    buffer = io.StringIO()
    call_command('seed_demo_data', *(['--reset'] if fresh else []), stdout=buffer)
    out.write('Demo company ready (login list: python manage.py seed_demo_data).\n')


def main(argv=None, out=None):
    out = out or sys.stdout
    parser = argparse.ArgumentParser(prog='regression.py selenium', description='Run every Selenium test case.')
    parser.add_argument('--only', action='append', help='ST-125, TC-24 or part of a test name (repeatable)')
    parser.add_argument('--list', action='store_true', help='show the test cases, run nothing')
    parser.add_argument('--fresh-demo', action='store_true', help='rebuild the demo company first')
    parser.add_argument('--no-preflight', action='store_true', help='skip the "are the servers running" check')
    args = parser.parse_args(argv)

    suite = load_tests(args.only)
    tests = list(_all_tests(suite))
    if args.list:
        for test in tests:
            doc = getattr(getattr(test, test._testMethodName, None), '__doc__', '') or ''
            parts = test.id().split('.')
            out.write(f'{story_label(parts[0]):<10} {tc_label(test.id(), doc):<6} {parts[-1]}\n')
        out.write(f'{len(tests)} test cases in {len(module_names())} files.\n')
        return 0
    if not tests:
        out.write('No test case matches. Use --list to see them.\n')
        return 2

    out.write(f'Selenium regression: {len(tests)} test cases. Frontend {helpers.FRONTEND_URL}, backend {helpers.BACKEND_API_URL}\n')
    if not args.no_preflight and not preflight(out):
        return 2
    ensure_demo_company(out, args.fresh_demo)

    result = LineResult(out)
    started = time.time()
    suite.run(result)
    counts = defaultdict(int)
    for row in result.rows:
        counts[row[0]] += 1
    out.write(f"\n{'-' * 60}\n")
    out.write(f"{counts['PASS']} passed, {counts['FAIL']} failed, {counts['ERROR']} errors, {counts['SKIP']} skipped "
              f'in {time.time() - started:.0f}s\n')
    bad = [r for r in result.rows if r[0] in ('FAIL', 'ERROR')]
    for status, story, tc, name, _s, note in bad:
        out.write(f'  {status} {story} {tc} {name}: {note}\n')
    clash = duplicate_tc_numbers([(r[1], r[2]) for r in result.rows])
    if clash:
        out.write('Note: these TC numbers are used by more than one story: ' +
                  '; '.join(f'{tc} in {", ".join(s)}' for tc, s in sorted(clash.items())) + '\n')
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
