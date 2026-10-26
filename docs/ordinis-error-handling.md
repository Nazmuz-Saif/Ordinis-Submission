# Ordinis — Error Handling & Edge Case Reference

এই ডকুমেন্ট coding করার সময় reference হিসেবে ব্যবহার করবে — প্রতিটা module বানানোর সময় এখানে চেক করে দেখবে সংশ্লিষ্ট error scenario handle করা হয়েছে কিনা।

## Delivered status (end of Sprint 5)

What the delivered system does for each scenario below. "Done" is backed by a test.

| Scenario | Status | Note |
|---|---|---|
| Standard success and error envelope with a `code` | Done | `core/exceptions.py` |
| Employee reports to themselves or a cycle | Done | Refused on save |
| Employee with a team is removed | Partly | Deletion is blocked; there is no "reassign the team" prompt |
| Role deleted while employees hold it | Done | Refused with code `ROLE_IN_USE` (409) and the number of holders; the Role stays (ST-139). The system CEO role and a Role used by a chain step are also protected |
| A Department or Designation deleted while employees still use it | Done | Refused with code `DEPARTMENT_IN_USE` or `DESIGNATION_IN_USE` (409) and a message that names who is in it (ST-150); nothing is cleared silently |
| A suspend, activate or ticket resolution without a note | Done | Refused with `NOTE_REQUIRED`, `NOTE_TOO_SHORT` (under 10 characters) or `NOTE_TOO_LONG` (over 255, 500 for a resolution) and nothing changes; the note is saved in the action log, and a ticket's resolution note is shown to the person who raised it (ST-154) |
| Setup order (Department before Employee) | Not enforced | Employees can be created without a department |
| Approval chain with no steps | Done | Leave uses the CEO fallback; other starts are refused |
| Approver left the company or nobody holds the role | Done for leave | The CEO fallback chain is used (ST-129) |
| Two people decide the same step at once | Done | Database unique constraint; the second gets "already decided" |
| Delegate and original holder both act | Done | Both allowed by design; neither can decide their own request |
| Two people edit one task at once | Not built | No optimistic locking |
| Progress outside 0 to 100 | Done | Validated |
| Assignee removed, task flagged for reassignment | Not built | |
| Invalid task status move | Done | Clear message |
| Second check-in the same day | Done | Refused |
| Leave over the balance, with the days left in the message | Done | Also checked per calendar year |
| End date before start date | Done | Serializer and database constraint |
| Leave on a holiday | Not applicable | The Holiday Calendar is not built |
| Payroll generated twice for one month | Done | Service check and database unique constraint |
| Payroll with incomplete attendance warning | Not built | Payslips do not read attendance |
| Negative or excessive deduction | Done | Between 0 and the gross amount |
| Background job crash, retries, idempotent jobs | Not applicable | No background jobs (no Celery) |
| Email failure fallback | Not applicable | No email channel |
| Employee added beyond the plan's limit | Done | Refused with an "upgrade your plan" message (code `PLAN_LIMIT_REACHED`); nothing is created; tested at exactly full and over |
| A plan too small for the current team | Done | A downgrade is refused while there are more employees than the plan allows |
| A plan upgrade: the extra amount, an upgrade paid after the period ended, the last day, two upgrades at once | Done | The extra amount is (new monthly price - current monthly price) x days left / 30, rounded to the taka, from the server's `upgrade-quote` (ST-151). Refused with `UPGRADE_NOT_HIGHER` (same or lower plan), `UPGRADE_NO_DAYS_LEFT` (nothing to charge on the last day), `PLAN_CHANGE_NOT_AVAILABLE` (the period is not running); one pending payment per company still holds (`PAYMENT_ALREADY_PENDING`); approving after the period ended is refused (`UPGRADE_PERIOD_ENDED`); the end date never changes |
| A lower plan | Done | Starts at the next renewal, never at once: `Subscription.next_plan`, billed by the renewal invoice and started by the first request or the daily job after the new period begins. Refused with `PLAN_TOO_SMALL` while the team is larger than the plan's limit, with `DOWNGRADE_NOT_LOWER` for a higher plan; it can be cancelled until its renewal is paid (`DOWNGRADE_ALREADY_PAID` after) (ST-151) |
| Subscription ends: a grace period, then a restricted mode | Done | 3 grace days after the end date, then only Billing, profile and support work (code `SUBSCRIPTION_RESTRICTED`, 403); it is not a read-only mode and not Suspend. The check runs on every request, so it holds even when the daily job did not run (ST-145) |
| A payment submitted twice, two at once, approved twice, or with a changed amount | Done | Manual payments (ST-146): a transaction id counts once per method (code `PAYMENT_TRANSACTION_USED`), one pending submission per company (`PAYMENT_ALREADY_PENDING`), the amount is always the server's quote (`PAYMENT_AMOUNT_MISMATCH` if the client's differs), approving twice changes nothing (locked row), all backed by database constraints |
| The renewal invoice issued twice, paid twice, or left open after an early renewal | Done | The daily job issues it once 7 days before the end (idempotent per period), an invoice can have only one live payment, approving marks the same invoice Paid, and an invoice covered by an early renewal is voided (ST-149) |
| Payment failure, webhooks | Not built | There is no payment gateway; payments are made outside the system and approved by the platform team |
| File too large or wrong type, storage down | Not applicable | No file upload |
| Another company's id in the URL | Done | 404, tested for every object route |
| Expired JWT | Done | 401, refresh flow |
| Brute-force login throttling and lockout | Not built | |

---


## 1. API Response Standard (সব endpoint-এ Consistent থাকবে)

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Task created successfully."
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "APPROVAL_CHAIN_NOT_CONFIGURED",
    "message": "This company has no approval chain set up for leave requests.",
    "field_errors": {}
  }
}
```

`code` field সবচেয়ে গুরুত্বপূর্ণ — এটা দিয়ে frontend নির্দিষ্ট UI/action দেখাতে পারবে, শুধু generic "Something went wrong" মেসেজ না দেখিয়ে। `core/exceptions.py`-এ একটা central **Error Code Registry** রাখা হবে যাতে সব app একই naming convention মেনে চলে (যেমন `MODULE_PROBLEM_DESCRIPTION` ফরম্যাটে — `ATTENDANCE_ALREADY_MARKED`, `TASK_INVALID_STATUS_TRANSITION`)।

---

## 2. Module-wise Error Scenarios

### Organization / RBAC
| Scenario | Handle করার উপায় |
|---|---|
| Employee নিজের `reports_to` হিসেবে নিজেকেই set করার চেষ্টা করলে (circular reference) | Save করার আগে validation — hierarchy তে loop তৈরি হচ্ছে কিনা চেক করা |
| একজন Employee-কে deactivate করা হলো, কিন্তু তার under-এ অন্য Employee আছে | Deactivate করার আগে বাধ্যতামূলকভাবে জিজ্ঞেস করবে "নিচের সবাইকে নতুন manager assign করো" — orphan hierarchy তৈরি হতে দেওয়া যাবে না |
| Role delete করা হচ্ছে, কিন্তু সেই Role-এ এখনো Employee assigned আছে | Delete block করবে, অথবা affected employee-দের list দেখিয়ে confirm করাবে |
| Company-তে কোনো Designation/Department তৈরি না করেই Employee add করার চেষ্টা | Setup Wizard order enforce করবে — আগে Department/Designation, পরে Employee |

### Workflow / Approval Engine
| Scenario | Handle করার উপায় |
|---|---|
| Approval Chain-এ কোনো Step সেট করা নেই | Fallback: default ভাবে CEO-র কাছে যাবে + Setup Wizard-এ persistent warning দেখাবে |
| Approval Chain-এ যাকে Approver বানানো হয়েছে, সে company থেকে exit করে গেছে | System detect করে পরের valid approver-কে (বা CEO-কে) route করবে |
| একই Approval Instance-এ দুইজন একসাথে Approve/Reject করার চেষ্টা করলে | Database-level lock/transaction — প্রথম action-ই valid হবে, দ্বিতীয়জন "already processed" error পাবে |
| Delegation Rule চলাকালীন Original Employee নিজেও Approve করার চেষ্টা করলে | Delegation active থাকা অবস্থায় Original owner-এর action block/warn করা (অথবা company-policy অনুযায়ী উভয়কেই allow করা) |

### Task Management
| Scenario | Handle করার উপায় |
|---|---|
| দুইজন একই সাথে একই Task edit করছে (Concurrent Edit) | Optimistic locking — প্রথম save successful হবে, দ্বিতীয়জন "data পুরনো হয়ে গেছে, refresh করো" error পাবে |
| Task-এ Progress % 100-এর বেশি বা ঋণাত্মক দেওয়ার চেষ্টা | Field-level validation (0–100 range enforce) |
| Assigned Employee deactivate হয়ে গেছে, কিন্তু তার Task এখনো pending | Task automatically flagged "needs reassignment", Department Head-কে notify |
| Invalid status transition (যেমন "Completed" থেকে সরাসরি "Not Started"-এ) | State machine validation — শুধু নির্দিষ্ট transition-ই allow করা |

### Attendance & Leave
| Scenario | Handle করার উপায় |
|---|---|
| একই দিনে দুইবার Check-in করার চেষ্টা | Duplicate detection — দ্বিতীয়বার "already checked in today" error |
| Leave balance-এর চেয়ে বেশি দিন Leave apply করলে | Submit করার আগে balance check, exceed করলে block বা HR-warning সহ allow (policy-dependent) |
| Leave-এর Start Date, End Date-এর পরে হলে | Field-level validation |
| Holiday-তে Leave apply করলে (যেটা এমনিতেই ছুটি) | Redundant বলে flag করা, কিন্তু block না করা |

### Payroll (Optional Module)
| Scenario | Handle করার উপায় |
|---|---|
| একই মাসের Payroll দুইবার Generate করার চেষ্টা | Duplicate-prevention — "already generated for this month" error, বা "regenerate" হিসেবে explicit confirm লাগবে |
| Salary Generate করার সময় Attendance data অসম্পূর্ণ (মাস শেষ হয়নি) | Warning দেখাবে, কিন্তু override করার option থাকবে (manual force-generate) |
| Payroll Policy-তে ভুল/conflicting rule সেট করা (যেমন deduction amount negative) | Policy save করার সময় validation |

### Notification & Background Jobs (Celery)
| Scenario | Handle করার উপায় |
|---|---|
| Celery worker crash করে কোনো background job (payroll generate, reminder) অর্ধেক সম্পন্ন হয়ে থেমে গেলে | Task **idempotent** ভাবে design করা (একই task দুইবার চালালেও ডাবল effect না হয়) + automatic retry (৩ বার) |
| Email notification পাঠানো fail হলে (SMTP down) | In-app notification সবসময় fallback হিসেবে কাজ করবে, email শুধু extra channel |
| একসাথে অনেক notification তৈরি হলে (Bulk announcement) | Queue-based asynchronous processing, UI ব্লক হবে না |

### Billing / Subscription
| Scenario | Handle করার উপায় |
|---|---|
| Payment Gateway (SSLCommerz) থেকে payment fail response এলে | Retry option + email notification, subscription সাথে সাথে বন্ধ না করে **Grace Period** (৩–৭ দিন) দেওয়া |
| Subscription মাঝপথে expire হয়ে গেলে (কাজ করার সময়) | **Read-only mode** — ডেটা হারাবে না, কিন্তু নতুন কিছু create করা যাবে না, যতক্ষণ না renew হয় |
| Employee সংখ্যা Plan-এর limit ছাড়িয়ে গেলে (যেমন Basic Plan-এ ১০ জনের বেশি) | নতুন Employee add করার আগে limit check, exceed করলে "upgrade your plan" prompt |
| Webhook (payment confirmation) দেরিতে বা duplicate আসলে | Idempotency key ব্যবহার করে duplicate payment record রোধ করা |

### File Upload (Task Attachment, Document)
| Scenario | Handle করার উপায় |
|---|---|
| খুব বড় ফাইল আপলোড করলে | Frontend + Backend দুই জায়গায় size limit validation (যেমন ১০ MB) |
| ভুল ফরম্যাট (executable file আপলোড করার চেষ্টা) | Whitelist-based file-type validation, শুধু নির্দিষ্ট extension allow |
| Storage (S3/Cloudinary) সাময়িকভাবে down থাকলে | Clear error message + retry button, upload আবার শুরু করা যাবে এমন UX |

### Multi-Tenancy / Security
| Scenario | Handle করার উপায় |
|---|---|
| একজন ইউজার URL manipulate করে অন্য company-র data access করার চেষ্টা করলে | প্রতিটা queryset বাধ্যতামূলকভাবে `company_id` দিয়ে filter হবে (middleware level enforce) — এমনকি ID সঠিক থাকলেও অন্য company-র হলে **404** (403 না, যাতে existence leak না হয়) |
| JWT token expire হয়ে যাওয়ার পর request এলে | Standard 401 + refresh token flow trigger |
| Rate limit exceed (Brute-force login attempt) | login endpoint-এ throttling, নির্দিষ্ট সংখ্যক ভুল চেষ্টার পর temporary lockout |

---

## 3. Global Error Handling Principle

1. **কখনো silent fail না** — প্রতিটা error হয় user-কে দেখানো হবে, নাহলে log হবে (বা দুটোই)
2. **User-facing message আলাদা, internal log আলাদা** — user দেখবে "Something went wrong, please try again", কিন্তু Sentry/log-এ পুরো stack trace থাকবে
3. **Security-sensitive error-এ details কম দেখানো** — যেমন login fail করলে "email or password incorrect" (কোনটা ভুল সেটা বলা যাবে না, নাহলে attacker email enumerate করতে পারবে)
4. **Idempotency যেখানে সম্ভব** — বিশেষ করে payment ও background job-এ, যাতে network retry হলে duplicate action না ঘটে

---

## এই Document কোথায় ব্যবহার হবে

- প্রতিটা app-এর `services.py` লেখার সময় এই টেবিল দেখে সংশ্লিষ্ট edge case handle করা আছে কিনা checklist হিসেবে ব্যবহার করবে
- `core/exceptions.py`-এ Error Code Registry বানানোর সময় base হিসেবে কাজ করবে
- Testing-এর সময় (`tests/`) এই scenario-গুলোই মূলত test case হিসেবে লেখা হবে
