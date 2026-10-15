# Testing Ordinis

Two commands, both run from the `backend` folder. Each prints one line per test case and ends with a non-zero
exit code if anything failed.

```
python regression.py backend      # every backend test (about 420, under a minute)
python regression.py selenium     # every browser test case (needs the two servers, see below)
python regression.py all          # backend first, then browser
```

**Never run a bare `python manage.py test`**: it would also pick up the browser tests in `backend/tests/`.

## Backend tests
- One-time: `pip install -r requirements.txt`, then `python manage.py migrate`.
- Besides each app's own tests, `core/test_api_matrix.py` checks **every API endpoint** (found automatically):
  1. no login gives 401 (only login, refresh, logout and register are public)
  2. an employee without the Permission gets 403, one with exactly that Permission gets past the check
  3. a user of another company gets 404 on every object of the demo company, and never sees it in a list
- Secure by default: `DEFAULT_PERMISSION_CLASSES` is "logged in + active company". A view that forgets
  `permission_classes` is closed, not open.

## Browser (Selenium) tests
1. Install Google Chrome. `pip install -r requirements.txt` (it includes `selenium`).
2. Start the backend: `python manage.py runserver` (in `backend`)
3. Start the frontend: `npm run dev` (in `frontend`). The tests expect `http://localhost:5173`.
   Other address: set `FRONTEND_URL=http://localhost:5174` (and `BACKEND_API_URL` for the API) before running.
4. Run: `python regression.py selenium`

Options: `--only ST-125` (one story), `--only TC-62` (one case), `--list` (show, do not run),
`--fresh-demo` (rebuild the demo company first), `--no-preflight`.
Before it starts it checks both servers answer, and makes sure the demo company exists.
Exit codes: 0 all passed, 1 a case failed or errored, 2 could not start (server down, nothing matched).

The browser opens for each test. `HEADLESS=1` hides it when a test uses `selenium_helpers.make_driver()`.

## Demo company (for the browser tests and for presenting)
`python manage.py seed_demo_data` builds "Acme Technologies Ltd." (run it again any time, nothing duplicates;
`--reset` rebuilds it, `--delete` removes it; other companies are never touched). Password for all: `Demo@12345`

| Role | Login |
|---|---|
| CEO | ceo@demo.ordinis.test |
| Manager | manager@demo.ordinis.test |
| HR | hr@demo.ordinis.test |
| Accountant | accountant@demo.ordinis.test |
| Employee | employee@demo.ordinis.test |
| Platform Admin | platform@demo.ordinis.test |

The same list is in `backend/apps/core/demo.py`; browser tests get it from `selenium_helpers.DEMO_USERS`.

## When you add something
- **A new app or endpoint**: nothing to register, the matrix finds it. It will fail until you (a) add
  `<app>/demo_data.py` with `ORDER` and `seed(ctx)` so there is a demo object to try, and (b) give each write
  endpoint a `permission_required`, or list it in `SELF_SERVICE` in `core/test_api_matrix.py` with the reason.
- **A new browser test**: any file `backend/tests/test_*.py` that uses `unittest` and `selenium` is picked up by its content, whatever its name. The TC number is read from the method name (`test_tcNN_what_it_checks`) or the file name (`test_stNNN_tcNN_...`)
  (the runner prints the TC number from the name). Use `from selenium_helpers import FRONTEND_URL, login, ...`.
  Do not define your own `FRONTEND_URL` or fill the login form yourself: `core/test_regression_tools.py` fails if you do.
  `login()` waits until the app leaves the login page, so it keeps working if the landing page changes.

## Known issues (found while building this, not fixed)
- TC-24, TC-25 and TC-26 are used twice (ST-112 and ST-115). The runner prints this note at the end.
- 17 of the 49 browser test cases have no TC number in their method or file name (all of ST-128 and most of the
  oldest files). They run and report, but show `-` in the TC column.
- `backend/tests/test_employee_roles.py` is an old script (needs `TEST_EMAIL`), not a test case; the runner skips it.
