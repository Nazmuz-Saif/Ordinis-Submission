# Ordinis

A multi-tenant "Organization Operating System": each company builds its own departments,
designations, reporting lines, roles/permissions and approval chains, with no code change.

Stack: Django + Django REST Framework + JWT (backend), React + Vite + Tailwind (frontend).

## Run the backend

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # optional for local development
python manage.py migrate
python manage.py runserver
```

API root: `http://127.0.0.1:8000/api/v1/` (every endpoint except login/register needs a Bearer token).

## Run the frontend

```powershell
cd frontend
npm install
copy .env.example .env        # optional, only if the API is not on 127.0.0.1:8000
npm run dev
```

## Tests

Always give the app names. A plain `python manage.py test` finds 0 tests.

```powershell
cd backend
python manage.py test core tenants accounts organization rbac approvals tasks payroll attendance
```

Frontend checks: `npm run lint` and `npm run build`.

## Environment variables (backend/.env)

| Variable | Meaning | Default (development) |
|---|---|---|
| `DJANGO_SECRET_KEY` | Secret key. **Required in production.** | insecure local key |
| `DJANGO_DEBUG` | `True` / `False` | `True` |
| `DJANGO_ALLOWED_HOSTS` | Comma separated hosts. **Required in production.** | empty |
| `CORS_EXTRA_ORIGINS` | Extra frontend origins, comma separated | empty |

Production: `DJANGO_SETTINGS_MODULE=config.settings.production` (refuses to start without the two required values).

## API notes

- Base path `/api/v1/`, JSON, `Authorization: Bearer <access token>`.
- List endpoints are paginated: `?page=2`, `?page_size=50` (default 20, max 100).
  Response: `{ "success": true, "data": [...], "pagination": { "count", "next", "previous" } }`.
- Errors: `{ "success": false, "error": { "code", "message", "field_errors" } }`.
- Another company's record is always a 404, never a 403.
- Every write action is checked against a Permission (for example `manage_employees`),
  never against a job title.

## Folders

```
backend/apps/   core, tenants, accounts, organization, rbac, approvals, tasks, attendance, payroll
frontend/src/   features/ (pages per module), services/ (API calls), components/, layouts/
```
