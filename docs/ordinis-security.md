# Ordinis — Security Reference (Top-Grade Security Checklist)

এই ডকুমেন্ট coding শুরু করার আগে এবং প্রতিটা module বানানোর সময় checklist হিসেবে ব্যবহার করবে। "Top-grade security" মানে একটা feature না, এটা প্রতিটা layer-এ ধারাবাহিকভাবে maintain করা একটা discipline।

## Delivered status (end of Sprint 5)

This checklist is the full target. The table says what the delivered system actually does. "Done" is backed by a test in the repository.

| Control | Status | Where / note |
|---|---|---|
| Password hashing (PBKDF2) | Done | Django default; a fast hasher only while tests run |
| MFA / TOTP | Not built | Future work |
| JWT access 15 min, refresh rotation, blacklist on logout | Done | `accounts` tests |
| Password reset flow | Not built | Future work |
| Account lockout after failed logins | Not built | Future work |
| Login error does not say which of email or password is wrong | Done | Wrong credentials give one message. A suspended company gets a specific message on purpose (FR-3) |
| Company password policy | Not built | Django validators only |
| Session list and "log out everywhere" | Not built | Future work |
| Tenant isolation, another company's object is 404 | Done | Every queryset filtered by company; `core/test_api_matrix.py` tries every object route |
| Permission check on every protected endpoint | Done | `PermissionRequiredMixin`; the matrix test checks 403 without it and success with exactly it |
| Closed by default (a forgotten permission is safe) | Done | `DEFAULT_PERMISSION_CLASSES` (found and fixed by the matrix test) |
| Least privilege: a new employee has no Permission | Done | Roles are assigned explicitly |
| Super Admin has no default access to client data (Break-Glass) | Done | Request, company approval, time limit, read-only, no salary data, access log |
| HTTPS / TLS | Not built | Production is not deployed |
| Field-level encryption (salary, NID) | Not built | Future work |
| Data export for an employee | Not built | Future work |
| Retention policy | Not built | Not defined |
| Backend input validation | Done | Serializers and services; the client cannot set owner, company, status |
| SQL injection | Done | Django ORM only, no raw SQL |
| XSS | Done | React escapes output; no user HTML is rendered |
| CSRF | Not needed | JWT in the `Authorization` header, no cookie session |
| Security headers (CSP, HSTS, X-Frame-Options) | Not built | Future work |
| Rate limiting | Not built | Future work |
| Webhook signature verification | Not built | No payment gateway |
| API versioning `/api/v1/` | Done | Every route |
| File upload security | Not applicable | No file upload exists; a task progress entry takes text and a link only |
| Append-only Audit Log | Not built | ST-135. Until then `ImpersonationLog`, `PlatformActionLog`, `ApprovalAction` have no edit or delete endpoint |
| Real-time alerting | Not built | Future work |
| Secrets in environment variables, none committed | Done | `backend/.env.example` |
| Dev / staging / production separation | Partly | `development.py` and a `production.py` template; production never run |
| Database user with least privilege, backups, dependency scanning | Not built | Future work |
| Terms of Service, privacy policy, penetration test | Not built | Before a commercial launch |

---


## 1. Authentication

| Control | বিস্তারিত |
|---|---|
| Password Hashing | Django default PBKDF2/Argon2 — plain text কখনোই store হবে না |
| **Multi-Factor Authentication (MFA/2FA)** | CEO, Accountant, HR, Super Admin-এর মতো high-privilege role-এর জন্য **বাধ্যতামূলক** (TOTP — Google Authenticator/Authy style); সাধারণ Employee-র জন্য optional |
| JWT Access + Refresh Token | Access token short-lived (~১৫ মিনিট), Refresh token rotation সহ, logout করলে blacklist |
| Password Reset Flow | Time-limited (১৫-৩০ মিনিট), single-use token, hashed token store (plain token database-এ কখনো না) |
| **Account Lockout Policy** | ৫টা ভুল login attempt-এর পর অ্যাকাউন্ট temporary lock (১৫-৩০ মিনিট) + email notification "someone tried to access your account" |
| Login Error Message | "Email অথবা Password ভুল" — কোনটা নির্দিষ্টভাবে ভুল বলা যাবে না (email enumeration আটকাতে) |
| Password Policy | Minimum length, complexity — company-level configurable (Enterprise client নিজের policy চাইতে পারে) |
| **Session Management** | Active session list দেখা যাবে (কোন device/location থেকে login) + "Logout from all devices" অপশন; Password change হলে অন্য সব session automatically invalidate |

---

## 2. Authorization (RBAC + Multi-Tenancy)

| Control | বিস্তারিত |
|---|---|
| Tenant Isolation | প্রতিটা queryset বাধ্যতামূলকভাবে `company_id` দিয়ে filter — middleware-level enforce, কোনো view individually trust করা যাবে না |
| Cross-Tenant Access Attempt | অন্য company-র resource ID দিয়ে অ্যাক্সেস করার চেষ্টা করলে **404** রিটার্ন হবে (403 না — resource-এর existence leak প্রতিরোধ করতে) |
| Permission Check | প্রতিটা protected endpoint-এ explicit permission-check decorator/class — "logged in আছে" যথেষ্ট না, "এই নির্দিষ্ট permission আছে কিনা" যাচাই বাধ্যতামূলক |
| Least Privilege Default | নতুন Employee তৈরি হলে default-এ **কোনো permission-ই থাকবে না**, explicit assign করতে হবে (opt-in, opt-out না) |
| Super Admin Access to Client Data | By default **কোনো access নেই** — "Break-Glass" pattern (Support Access Request → CEO approval → time-limited → logged) — আগেই design করা হয়েছে |

---

## 3. Data Protection

| Control | বিস্তারিত |
|---|---|
| Encryption in Transit | সব communication HTTPS/TLS 1.2+ বাধ্যতামূলক, HTTP থেকে HTTPS-এ auto-redirect |
| **Encryption at Rest (Field-Level)** | Salary amount, NID/passport-এর মতো অত্যন্ত sensitive field — শুধু database-level encryption না, **application-level field encryption** (যাতে DB access পেলেও raw data readable না হয়) |
| Database-level Encryption | PostgreSQL-এর disk-level encryption (managed hosting provider সাধারণত এটা দেয় — Render/AWS RDS) |
| PII Minimization | যতটুকু data সত্যিই দরকার ততটুকুই collect করা, "future-এ লাগতে পারে" ভেবে extra sensitive data না রাখা |
| **Data Export/Right to Access** | Employee নিজের সব data export করতে পারবে (PDF/JSON) — transparency ও future compliance-এর জন্য |
| Data Retention Policy | Company subscription cancel করলে ডেটা কতদিন রাখা হবে তারপর permanently delete — স্পষ্ট নীতি থাকা দরকার |

---

## 4. API & Application Security

| Control | বিস্তারিত |
|---|---|
| Input Validation | সব input backend-এ validate (frontend validation শুধু UX-এর জন্য, security-এর জন্য না — কখনো শুধু frontend-এর উপর ভরসা করা যাবে না) |
| SQL Injection | Django ORM ব্যবহার করলে by default প্রতিরোধ হয় — raw SQL query এড়ানো, লাগলে parameterized query বাধ্যতামূলক |
| XSS Protection | React auto-escape করে; Django template ব্যবহার হলেও autoescape on রাখা; user-generated content (task comment) sanitize করা |
| CSRF Protection | JWT-based auth হলে সাধারণত কম ঝুঁকি, কিন্তু কোনো cookie-based session ব্যবহার হলে CSRF token বাধ্যতামূলক |
| **Security Headers** | `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Strict-Transport-Security` (HSTS) — সব response-এ set করা |
| Rate Limiting | শুধু login না, সব sensitive endpoint-এ (password reset, payment, bulk export) throttling |
| **Webhook Signature Verification** | Payment gateway (SSLCommerz)-থেকে আসা callback-এর signature/hash যাচাই বাধ্যতামূলক — নাহলে কেউ fake "payment successful" callback পাঠিয়ে subscription activate করতে পারবে |
| API Versioning | `/api/v1/` — breaking change হলে নতুন version, পুরনো client হঠাৎ ভেঙে যাবে না |

---

## 5. File Upload Security

| Control | বিস্তারিত |
|---|---|
| **File Type Whitelist — Context-Aware, Company-Configurable** | Global fixed list না — কোথায় upload হচ্ছে (Profile Picture / Task Attachment / Document) তার উপর ভিত্তি করে আলাদা whitelist। Task Attachment-এর মতো context-এ Company নিজের প্রয়োজন অনুযায়ী extension যোগ করতে পারবে (যেমন developer company `.py`, `.js`, `.json`, `.zip` যোগ করবে; design agency `.psd`, `.fig` যোগ করবে) — এটা `FILE_UPLOAD_POLICY` entity দিয়ে data-driven রাখা হবে, hardcoded না |
| **System-Level Absolute Block (কখনো Override করা যাবে না)** | `.exe`, `.bat`, `.sh`, `.dll`, `.msi`-এর মতো executable extension — company override করতে পারলেও এগুলো সবসময় block থাকবে, কোনো context-এই allow না |
| Profile Picture / Document Module | এগুলোর জন্য fixed, non-configurable whitelist থাকবে (jpg/png/pdf) — নিরাপত্তা ও format-consistency-র কারণে company override করতে পারবে না |
| File Size Limit | Frontend + Backend দুই জায়গায় enforce, context অনুযায়ী ভিন্ন limit রাখা যাবে (Task Attachment বড় হতে পারে, Profile Picture ছোট) |
| **Malware/Virus Scanning** | Upload হওয়া ফাইল storage-এ যাওয়ার আগে scan করা (ClamAV বা cloud-provider-এর malware scanning service) — extension যাই হোক, এটা সবসময় প্রযোজ্য |
| Storage Isolation | Uploaded file **কখনো execute হবে না** — এমনকি `.py`/`.js`-এর মতো code file allow করা হলেও সেটা শুধু storage-এ (S3/Cloudinary) থাকবে, download/view-এর জন্য, কখনো server-এ run করার জন্য না — এটাই আসল নিরাপত্তা, শুধু extension block করা যথেষ্ট না |
| Signed URL | Sensitive document (payslip, contract) সরাসরি public URL না দিয়ে time-limited signed URL দিয়ে access দেওয়া |

---

## 6. Audit & Monitoring

| Control | বিস্তারিত |
|---|---|
| **Audit Log Immutability** | Audit Log কখনো edit/delete করা যাবে না — এমনকি Super Admin-ও না (append-only design; চাইলে hash-chain দিয়ে tamper-evidence যোগ করা যায়, প্রতিটা entry-তে আগের entry-র hash রাখা) |
| Comprehensive Logging | Login, permission change, salary update, data export, delete action — সব sensitive action log হবে (actor, timestamp, IP address, before/after যেখানে সম্ভব) |
| Real-time Alerting | অস্বাভাবিক pattern (একজন ইউজার হঠাৎ অনেক data export করছে, বা বারবার login fail হচ্ছে) হলে automatic alert (Sentry/email) |
| Impersonation Logging | Break-Glass access ব্যবহার হলে সব কিছু আলাদাভাবে, বেশি বিস্তারিতভাবে log হবে |

---

## 7. Infrastructure & Secrets

| Control | বিস্তারিত |
|---|---|
| **Secrets Management** | Production-এ `.env` ফাইল যথেষ্ট না — dedicated secret manager ব্যবহার করা ভালো (AWS Secrets Manager, অথবা অন্তত hosting provider-এর built-in environment variable encryption) |
| Never Commit Secrets | `.gitignore`-এ `.env` বাধ্যতামূলক, `.env.example` শুধু placeholder সহ কমিট হবে |
| Environment Separation | Dev/Staging/Production সম্পূর্ণ আলাদা database ও credential — কখনো production DB dev-এ connect করা যাবে না |
| Database User Least Privilege | Application-এর DB user-এর শুধু প্রয়োজনীয় permission (SELECT/INSERT/UPDATE), DROP/ALTER-এর মতো admin permission না |
| Dependency Vulnerability Scanning | GitHub Dependabot enable করা, নিয়মিত `pip-audit`/`npm audit` চালানো |
| Backup & Disaster Recovery | নিয়মিত automated database backup (daily), backup restore টেস্ট করে দেখা (backup আছে মানেই কাজ করবে তা না, restore test করা জরুরি) |

---

## 8. Compliance & Governance

| Control | বিস্তারিত |
|---|---|
| Terms of Service / Privacy Policy | Legal document থাকা দরকার (future business step, কিন্তু design-এ data handling policy-র সাথে consistent হতে হবে) |
| Data Processing Transparency | Company-কে স্পষ্টভাবে জানানো — কী data রাখা হচ্ছে, কীভাবে ব্যবহার হচ্ছে, Super Admin access কীভাবে কাজ করে (Break-Glass pattern) |
| Security Review Cadence | Production launch-এর আগে অন্তত একটা basic penetration test/security review করানো (নিজে অথবা third-party দিয়ে) |

---

## নতুন Entity যা ER Diagram-এ যোগ করা হলো (এই Review-এর ফলাফল)

```
TWO_FACTOR_AUTH
  - user_id (FK)
  - secret_key_encrypted
  - is_enabled (boolean)

ACTIVE_SESSION
  - user_id (FK)
  - session_token_hash
  - ip_address
  - device_info
  - last_active_at

COMPANY_IP_WHITELIST
  - company_id (FK)
  - ip_range
  - is_active

SECURITY_EVENT
  - user_id (FK)
  - event_type (failed_login / permission_denied / suspicious_export ইত্যাদি)
  - ip_address
  - created_at

FILE_UPLOAD_POLICY
  - company_id (FK, nullable — null হলে system default)
  - context (task_attachment / profile_picture / document ইত্যাদি)
  - allowed_extensions (JSON list)
  - max_file_size_mb
```

**Note:** `ordinis-full-ER-diagram.md`-এ ইতিমধ্যে `COMPANY_IP_WHITELIST` এবং `SECURITY_EVENT` entity সমান্তরালে যোগ হয়ে গিয়েছিল (Enterprise-level IP restriction ও আলাদা security-event tracking-এর জন্য) — এই ডকুমেন্টের সাথে সেগুলো align করা হয়েছে।

---

## Priority — কোনগুলো Course Project-এও এখনই করা উচিত (Minimum Viable Security)

সবকিছু একসাথে production-grade করা course timeline-এ সম্ভব না, কিন্তু এই কয়েকটা **কম effort, high impact** — এগুলো শুরু থেকেই রাখা উচিত:

1. ✅ Tenant isolation (company_id filtering) — এমনিতেই core design-এর অংশ
2. ✅ Password hashing (Django default) — বিনামূল্যে পাওয়া যায়
3. ✅ JWT + permission-check decorator
4. ✅ 404 (403 না) cross-tenant attempt-এ
5. ✅ Input validation
6. ⚠️ MFA — শুধু CEO/Admin role-এর জন্য basic TOTP implement করলেই যথেষ্ট demo-র জন্য
7. ⚠️ Security headers — Django middleware দিয়ে ২ লাইনে করা যায়, করে ফেলাই ভালো

বাকি (webhook signature, malware scanning, secret manager, penetration testing) — এগুলো **production/commercial launch-এর আগে** করলেই চলবে, course demo-র জন্য critical না।
