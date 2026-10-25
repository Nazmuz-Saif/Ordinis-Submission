# Ordinis — Role-wise Dashboard Design (Detailed)

প্রতিটা role-এর dashboard আলাদা হবে কারণ তাদের কাজ ও প্রয়োজন আলাদা। নিচে প্রতিটা role-এর জন্য কী কী দেখবে, কী কী করতে পারবে (access/permission) তা বিস্তারিত দেওয়া হলো।

**Note (Design Update):** নিচের প্রতিটা "Role" (CEO, GM, HR ইত্যাদি) আসলে একটা **Designation + নির্দিষ্ট Permission Set-এর সমন্বয়**। Dashboard-এ কোন Widget/Option দেখা যাবে তা মূলত সেই ব্যবহারকারীর **assigned Permission** (যেমন: `view_finance`, `approve_leave`, `manage_users`) অনুযায়ী নির্ধারিত হবে, শুধু তার Designation-এর নাম দেখে না। তাই একই company-তে একজন "Senior Developer" ডিজাইনেশনের কেউ যদি তাকে "Approver" Role/Permission দেওয়া হয়, সে Department Head-এর মতো কিছু Approval feature-ও দেখতে পারবে।

## Delivered status (end of Sprint 5)

One endpoint, `GET /api/v1/dashboard/summary/`, returns sections chosen by the user's **Permissions**, not by Designation. A user can hold several sections. Tests check that each role gets only its sections and that an employee's response contains no salary text.

| Role in this document | Status | What the delivered system does |
|---|---|---|
| Super Admin | Built | Dashboard home (companies by state, revenue this month and all time, dues, subscriptions ending, pending payments, open tickets, revenue per month, a Needs attention list: ST-153), Companies list and detail page, suspend and activate with a note, Payments, Subscriptions, support tickets, Break-Glass access requests, activity log. Platform announcements and a sign-up trend: not built, future |
| CEO / Company Owner | Built | All sections, approvals waiting, Support Access approve, deny and revoke. Budget and expense snapshot, department comparison, company health score, activity feed: not built |
| CTO, GM, AGM | No separate dashboard | They get the sections their Permissions give (for example the Manager section); no role-specific screen |
| HR | Built | `people` section (headcount, joiners). Document verification list, holiday calendar, attendance policy: not built |
| Department Head | Built | `team` section (team tasks, approvals waiting). The daily progress timeline per task is on the Tasks screen. Weekly reports to the GM: not built |
| Accountant | Built | `finance` section; no task or HR data. Expense and reimbursement: not built |
| Employee | Built | `me` section (today's tasks, deadlines, attendance, leave balance, notifications, payslips). Company announcements and direct messages: not built |
| Common profile settings | Partly | Everyone can log out and see their own data. Change password, notification preferences, active sessions, MFA: not built |

---


## 1. Super Admin Dashboard (আমাদের Platform Owner Team)

**মনে রাখতে হবে:** Super Admin কোনো company-র operational কাজে (task, attendance, salary) হস্তক্ষেপ করবে না। তার কাজ পুরোপুরি **platform-level**।

### দেখতে পারবে
- মোট কতগুলো Company (client) registered আছে
- প্রতিটা Company-র Subscription Plan ও Status (Active/Expired/Trial)
- মাসিক/বাৎসরিক মোট Revenue (Billing Overview)
- নতুন Sign-up-এর Trend (Growth Analytics)
- কোন Company Payment Pending/Overdue আছে
- System-wide uptime/error log (Technical Health, optional)

### করতে পারবে (Actions)
- নতুন Company Account Approve/Reject করা (যদি manual verification রাখা হয়)
- কোনো Company Suspend/Activate করা (Payment না দিলে)
- Subscription Plan পরিবর্তন/Upgrade করে দেওয়া (client request করলে)
- Client-এর Support Ticket/Complaint দেখা ও reply করা
- Platform-wide Announcement পাঠানো (সব Company-কে, যেমন "নতুন ফিচার যোগ হয়েছে")
- **Support Access Request পাঠানো** — কোনো company-তে bug/issue-এর report এলে, সরাসরি ঢুকে না গিয়ে "Access Request" পাঠাবে (reason সহ)

### by Default দেখতে পারবে না, কিন্তু প্রয়োজনে Controlled Access নিতে পারবে (Break-Glass Pattern)

Company-র ভিতরের employee task, attendance, salary — এগুলো by default Super Admin দেখতে পারবে না (Data Privacy/Isolation নীতি)। কিন্তু তোমার (Nexoria/Ordinis owner হিসেবে) genuine প্রয়োজন আছে bug fix বা misuse-monitoring করার জন্য — সেটা এভাবে সমাধান হবে:

```
Client কোনো সমস্যায় পড়লে (bug report করলে)
  ↓
Super Admin "Support Access Request" পাঠায় (reason লিখে: "Bug #123 fix করার জন্য অ্যাক্সেস দরকার")
  ↓
সেই Company-র CEO notification পায়, Approve/Deny করে
  ↓
Approve করলে — Super Admin সাময়িক, সময়-সীমিত (যেমন ২৪ ঘণ্টা) access পায়
  ↓
এই সময়ের মধ্যে যা কিছু দেখে/করে, সব "Impersonation Log"-এ record হয়
  ↓
সময় শেষ হলে access automatically বন্ধ হয়ে যায়
  ↓
CEO চাইলে পরে দেখতে পারবে Super Admin ঠিক কী দেখেছিল/করেছিল
```

**এভাবে করার সুবিধা:**
- তুমি তোমার আসল প্রয়োজন (bug fix, misuse-monitor) মেটাতে পারবে
- Client-কে সততার সাথে বলতে পারবে "By default আমরা তোমার employee data দেখি না, শুধু তোমার অনুমতি নিয়ে, সময়-সীমিত ও সম্পূর্ণ log-সহ দেখি"
- এটা enterprise client বিশ্বাস অর্জনে সাহায্য করবে এবং legal ঝুঁকি কমাবে

**Emergency ক্ষেত্রে (System down, data corruption-এর মতো critical bug):** CEO approval-এর জন্য অপেক্ষা না করে সরাসরি emergency override নেওয়া যাবে, কিন্তু সেটা তৎক্ষণাৎ company-কে notify করবে এবং প্রতিটা action আরও কড়াকড়িভাবে log হবে।

---

## 2. CEO / Company Owner Dashboard

CEO-র dashboard হবে সবচেয়ে **comprehensive এবং high-level overview-ভিত্তিক** — সে ডিটেইলে না গিয়ে পুরো company-র স্বাস্থ্য এক নজরে বুঝতে পারবে।

### Dashboard-এ যা দেখবে (Widgets)
- **Company Overview** — মোট Department, মোট Employee সংখ্যা
- **Pending Approvals** (তার কাছে আসা)
- **Active Projects/Tasks Summary**
- **Department-wise Performance Comparison** (কোনটা এগিয়ে, কোনটা পিছিয়ে)
- **Attendance Summary** (আজ কতজন উপস্থিত/অনুপস্থিত)
- **Leave Requests Summary**
- **Company Health Score** (task completion + attendance মিলিয়ে)
- **Recent Activity Feed** (কে সম্প্রতি কী করেছে)
- **Budget/Expense Snapshot** (যদি Accountant role active থাকে)

### করতে পারবে (Full Access — Company-র মধ্যে সর্বোচ্চ)
- Company Structure তৈরি/পরিবর্তন (Department, Designation যোগ/বাদ)
- যেকোনো Employee-র id তৈরি (অথবা HR-কে delegate করা)
- যেকোনো role-এর Permission Customize করা
- High-priority Task/Project তৈরি করে GM-কে assign করা
- চূড়ান্ত Budget Approval দেওয়া
- Company-wide Announcement/Policy Publish করা
- **হায়ারার্কির সব স্তরের ডেটা দেখা** (GM, Dept Head, HR, Accountant, Employee — সবার activity, কারণ CEO সবার উপরে)
- Subscription/Billing নিজে manage করা (plan upgrade, payment history দেখা)
- **Company Settings ঠিক করা** (Currency, Timezone, Fiscal Year Start — নতুন যোগ হওয়া `COMPANY_SETTINGS`)
- **Setup Wizard-এ Role Template বেছে নেওয়া** (Startup/Enterprise preset দিয়ে শুরু করা, পরে customize করা যাবে — নতুন `ROLE_TEMPLATE`)
- **Support Access Request Approve/Deny করা** — Super Admin bug fix-এর জন্য অ্যাক্সেস চাইলে সেটা review করে অনুমতি দেওয়া বা না দেওয়া, এবং পরে Impersonation Log দেখে যাচাই করা কী করা হয়েছিল

---

## 3. CTO (যদি company এই role রাখে)

*(তোমার প্রশ্নে CTO উল্লেখ ছিল — এটা optional designation হিসেবে company চাইলে যোগ করতে পারবে, বিশেষত Software/Tech company-র ক্ষেত্রে)*

### দেখবে
- Technical/Development Department-এর সব প্রজেক্ট ও Task status
- Development Team-এর Workload ও Progress
- Bug/Issue Tracking Summary (যদি এমন module থাকে)

### করতে পারবে
- Development-related Task তৈরি ও Dept Head-কে Assign
- Technical Project Approve/Review
- Development Team-এর কাউকে নিয়োগ/promote করার জন্য CEO-কে Request পাঠানো

**Note:** CTO মূলত GM-এর মতোই একটা **branch-specific উচ্চ পর্যায়ের role**, শুধু তার scope Technical Department-এর মধ্যে সীমাবদ্ধ থাকতে পারে (company যেভাবে configure করবে)।

---

## 4. GM (General Manager) Dashboard

### দেখবে
- সব Department-এর Progress Summary (CEO-র থেকে সামান্য কম high-level, কিন্তু operational detail বেশি)
- Department Head-দের Submitted Weekly/Monthly Report
- Pending Approval (তার কাছে আসা task/budget approval)
- Team Performance Comparison (Department-wise)

### করতে পারবে
- Department Head-দের Task/Project Assign করা
- প্রজেক্ট তৈরি করা (CEO-র নির্দেশনা অনুযায়ী)
- Department Progress Review ও Feedback দেওয়া
- Budget Request পাঠানো (CEO-র কাছে Approval-এর জন্য)
- নিজের নিচের সব লেভেলের (Dept Head, Employee) ডেটা দেখা

### দেখতে পারবে না
- Billing/Subscription তথ্য (এটা শুধু CEO-র access)
- অন্য কোনো high-level role-এর (যদি আরেকজন GM থাকে অন্য branch-এ) ডেটা, যদি company সেভাবে আলাদা না রাখে

---

## 5. AGM (Assistant GM) Dashboard

মূলত GM Dashboard-এর **প্রায় হুবহু কপি**, কিন্তু কিছু critical action-এ সীমাবদ্ধতা থাকবে।

### দেখবে
GM-এর মতোই সব কিছু (Department progress, reports, approvals)।

### করতে পারবে
- GM-এর delegated কাজ করা (GM ছুটিতে থাকলে Delegation Engine-এর মাধ্যমে GM-এর pending approval তার কাছে আসবে)
- Task review/monitor করা

### সীমাবদ্ধতা
- চূড়ান্ত Budget Approval করতে পারবে না (এটা GM/CEO-র অধিকার, যদি company এভাবে define করে)
- Company Structure change করার অধিকার থাকবে না

---

## 6. HR Dashboard

HR-এর dashboard সম্পূর্ণ **আলাদা ধরনের** — এটা hierarchy-position না, বরং **functional/employee-lifecycle-কেন্দ্রিক**।

### দেখবে
- মোট Employee সংখ্যা, নতুন Joining, Exit-এর তালিকা
- Pending Leave Requests (Approval-এর জন্য অপেক্ষারত)
- Document Verification Pending List
- Holiday Calendar
- Department-wise Headcount

### করতে পারবে
- নতুন Employee Onboard করা (id তৈরি — যদি CEO delegate করে)
- Employee Exit Process করা
- Leave Approve/Reject করা (Approval Chain-এর একটা ধাপ হিসেবে)
- Promotion/Transfer Record আপডেট করা
- Employee Document আপলোড/verify করা
- Company Policy/Notice Publish করা
- **Attendance Policy সেট করা** (late-penalty rule, leave carry-forward rule ইত্যাদি — নতুন `ATTENDANCE_POLICY`)

### দেখতে পারবে না
- Salary/Payroll-এর সংখ্যাগত ডিটেইল (এটা Accountant-এর কাজ, যদি company সেভাবে আলাদা রাখে — HR শুধু employee record দেখবে, টাকার হিসাব না)
- Task/Project-এর technical progress (এটা Dept Head/GM-এর scope)

---

## 7. Department Head Dashboard

### দেখবে
- নিজের Department-এর সব Employee-র Task List ও Progress
- Pending Task Review
- Today's Deadline
- নিজের Team-এর Attendance
- Leave Request (তার Department-এর Employee-দের থেকে আসা, প্রথম approval ধাপ)
- **Multi-day Task-এর Daily Progress Log Timeline** (কোনো Employee ৭ দিনের Task করলে, প্রতিদিনের update এখানে timeline আকারে দেখা যাবে, code upload ছাড়াই)

### করতে পারবে
- নিজের Department-এর Employee-দের Task তৈরি ও Assign করা
- Deadline নির্ধারণ/পরিবর্তন করা
- Submitted Task Review, Approve/Reject করা
- Leave Request-এ প্রথম-স্তরের Approval দেওয়া
- Weekly/Monthly Report তৈরি করে GM-কে Submit করা

### দেখতে পারবে না
- অন্য Department-এর কোনো ডেটা (শুধু নিজের department-এর মধ্যে সীমাবদ্ধ — এটাই hierarchy-based isolation-এর ভালো উদাহরণ)
- Salary/Budget তথ্য (যদি না company আলাদা করে অধিকার দেয়)

---

## 8. Accountant Dashboard (আলাদা থাকলে)

আগে যেটা বলেছিলাম — এটা **Optional role**, ছোট company-তে CEO নিজেই এই কাজ করবে। আলাদা Accountant থাকলে তার dashboard হবে:

### দেখবে
- Payroll Summary (এই মাসের মোট salary payout)
- Pending Salary Generation (কোন employee-র salary এখনো process হয়নি)
- Expense/Reimbursement Requests (pending)
- Budget vs Actual Spending Overview

### করতে পারবে
- প্রতিটা Employee-র Salary Generate করা (Attendance/Leave record অনুযায়ী automatic calculation হলে ভালো)
- Salary Slip তৈরি ও Employee-কে পাঠানো
- Expense/Reimbursement Approve করা
- Payroll Report তৈরি করে CEO/GM-কে Submit করা
- **Payroll Policy সেট করা** (leave-based deduction rule, tax slab ইত্যাদি — নতুন `PAYROLL_POLICY`)

### দেখতে পারবে না (এটাই গুরুত্বপূর্ণ RBAC উদাহরণ)
- কোনো Employee-র Task/Project ডেটা
- কোনো Department-এর Performance/Progress তথ্য
- Employee-র personal HR record (leave history বাদে, যদি salary calculation-এর জন্য প্রয়োজন না হয়)

**Accountant-এর id কেমন হবে:** এটা একটা functional/special-purpose account — hierarchy-তে তার position (কে তার under-এ, কার under-এ সে) matter করে না তেমন, বরং তাকে দেওয়া হবে শুধুমাত্র **"Finance Module Access"** permission। Login করলে তার dashboard-এ শুধু Finance-সংক্রান্ত মেনু-ই দেখাবে, বাকি সব option hide থাকবে।

---

## 9. Employee Dashboard (Multiple Department-এর সবার জন্য একই কাঠামো)

Employee Dashboard হবে সবচেয়ে **Simple ও Minimal**, যেন সে সহজে বুঝে ব্যবহার করতে পারে।

### দেখবে
- **Today's Tasks** (আজকে তার কী কী কাজ আছে)
- **My Deadlines** (আসন্ন deadline)
- **My Attendance** (এই মাসের attendance record)
- **Leave Balance** (কতদিন ছুটি বাকি আছে)
- **Notifications** (task update, approval status)
- **Company Announcements**
- **My Salary Slip** (আগের মাসগুলোর, যদি Accountant module থাকে)
- **Messages** (Company Directory থেকে যে কারো সাথে 1-to-1 direct message — Layer 3 future feature)

### করতে পারবে
- নিজের Task-এর Progress Update করা (%, status change)
- Task-এ Comment/File Upload করা
- **Multi-day Task-এ Daily Progress Log দেওয়া** (আজ কী করলাম — text update, progress %, blocker থাকলে সেটাও; চাইলে GitHub commit-এর মতো external reference link যোগ করা যাবে — কোনো code upload করতে হবে না)
- Leave Apply করা
- Attendance দেওয়া (check-in/check-out)
- নিজের Profile Update করা (ছবি, contact info ইত্যাদি)
- Daily/Weekly Report Submit করা (যদি company এটা চায়)

### দেখতে পারবে না
- অন্য কোনো Employee-র Task/Salary/Attendance
- Department-level বা Company-level কোনো Analytics/Report
- কোনো Approval/Management Feature

**Multiple Department-এর Employee হলে পার্থক্য কী?**
মূল কাঠামো (dashboard layout) সবার জন্য একই থাকবে, শুধু **Task List এবং "Reports To" ভিন্ন হবে** — একজন Development-এর Employee তার Development Department Head-এর অধীনে task পাবে, Marketing-এর Employee তার নিজের Head-এর অধীনে। System backend-এ এটা `department_id` এবং `reports_to` field দিয়ে আলাদা করা হবে, কিন্তু UI/Dashboard একই রকম দেখাবে সবার জন্য।

---

## 10. সবার জন্য Common — Profile / Account Settings (Role-নির্বিশেষে)

এই অংশটা Super Admin থেকে শুরু করে Employee পর্যন্ত **প্রতিটা role-এর Dashboard-এ একই জায়গায়, একইভাবে থাকবে** (সাধারণত top-right corner-এ "Profile" icon-এর নিচে):

- **Change Password** — পুরনো password verify করে নতুন সেট করা (নতুন `PASSWORD_RESET_TOKEN` entity এই flow-কেই সাপোর্ট করে)
- **Notification Preference** — কোন চ্যানেলে (In-app / Email) notification পেতে চায় সেটা on/off করা (নতুন `NOTIFICATION_PREFERENCE` entity)
- **Profile Picture ও Contact Info Update**
- **Active Sessions দেখা ও Revoke করা** (কোন device থেকে login করা আছে, সন্দেহজনক কিছু দেখলে সরাসরি সেই session logout করে দেওয়া যাবে — নতুন `ACTIVE_SESSION` entity)
- **Two-Factor Authentication (MFA) On/Off করা** — Authenticator app দিয়ে extra security layer যোগ করা, CEO/Accountant-এর মতো high-privilege role-এর জন্য company চাইলে বাধ্যতামূলকও করে দিতে পারবে (নতুন `TWO_FACTOR_AUTH` entity)
- **Company Directory ও Direct Message অ্যাক্সেস** (top navigation-এ) — company-র সব active Employee-র searchable list, সেখান থেকে যে কাউকে 1-to-1 message পাঠানো যাবে (hierarchy-restriction ছাড়া, সবার জন্য open — Layer 3 future feature)

এটা আলাদা কোনো role-specific dashboard section না, বরং **সব dashboard layout-এর একটা shared/common component** — তাই frontend-এ `layouts/` এর প্রতিটা Layout ফাইলে আলাদা করে না বানিয়ে, একটা shared `ProfileSettingsPanel` component (future, not built) বানিয়ে সবগুলোতে reuse করাই ভালো practice।

---

## সারসংক্ষেপ — Access Level Hierarchy (উপর থেকে নিচে)

| Level | Role | মূল ফোকাস | Visibility Scope |
|---|---|---|---|
| 0 | Super Admin | Platform পরিচালনা | সব Company-র Billing/Account (Operational data না) |
| 1 | CEO | পুরো Company | পুরো Company-র সব ডেটা |
| 2 | GM/CTO | Operational Execution | নিজের scope-এর সব Department |
| 2.5 | AGM | GM-কে সহায়তা | GM-এর প্রায় সমান, কিছু action সীমিত |
| Functional | HR | Employee Lifecycle | সব Employee-র HR-related তথ্য (salary বাদে) |
| Functional | Accountant | Financial | শুধু Payroll/Expense সংক্রান্ত তথ্য (task/HR বাদে) |
| 3 | Department Head | নিজের Team | শুধু নিজের Department-এর Employee |
| 4 | Employee | নিজের কাজ | শুধু নিজের ডেটা |

**মূলনীতি (Design Principle):** *"Vertical hierarchy তথ্য উপরে প্রবাহিত হয় (bottom-up visibility for management), কিন্তু functional role (HR, Accountant) হায়ারার্কি ভেদ করে শুধু নিজেদের কাজের ডেটা-তেই সীমাবদ্ধ থাকে (horizontal restriction)।"* — এই hybrid access model-টাই তোমার CEP-এর P2 (conflicting requirements) এবং A2 (interaction থেকে উদ্ভূত সমস্যা সমাধান)-এর সবচেয়ে ভালো practical প্রমাণ, presentation/viva-তে এটা emphasize করবে।
