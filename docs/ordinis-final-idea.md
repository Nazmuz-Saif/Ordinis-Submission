# Ordinis — Final Idea Summary (Presentation-Ready)

> **Vision and proposal document.** It describes the product idea and the full plan. What is actually delivered, requirement by requirement (Done, Partly, Not built), is in `Ordinis_SRS.md` Section 7.2, read from the code. Items here that are not built, for example the Workload Balancer, Delegation of every module, Company Setup Wizard steps and Organization Analytics, are future work.

## Project Title
**Ordinis — A Dynamic, Multi-Tenant Workflow & Chain-of-Command Configuration Platform**

**Tagline:** *"Build Your Organization. Define Your Workflow."*

**Product Positioning Statement:**
> *"Ordinis is a configurable Organization Operating System (OrgOS) that enables companies to design their own organizational hierarchy, workflows, permissions, and approvals — without changing the software."*

---

## 30-Second Opening Line (Presentation-এ প্রথমেই বলবে)

> "আমরা একটি ERP বানাচ্ছি না। আমরা একটি **Configurable Workflow Platform** বানাচ্ছি, যেখানে যেকোনো organization নিজের hierarchy, reporting structure, এবং approval workflow নিজেদের মতো করে configure করতে পারবে — কোনো fixed structure ছাড়াই। Payroll, CRM, Inventory-এর মতো module ভবিষ্যতে **plug-in** হিসেবে যোগ করা যাবে।"

এই একটা লাইনই scope-কে focused এবং engineering-oriented হিসেবে দাঁড় করাবে — শিক্ষক প্রথমেই বুঝবে তোমরা "সব কিছু বানানো" চেষ্টা করছো না, বরং একটা core engineering problem সমাধান করছো।

---

## Problem Statement

বর্তমানে অধিকাংশ Startup ও SME তাদের দৈনন্দিন office কার্যক্রম (task tracking, approval, reporting) পরিচালনা করে বিক্ষিপ্তভাবে — WhatsApp, Excel, Google Sheets ব্যবহার করে। এর ফলে:

- Chain of command স্পষ্ট থাকে না, accountability কমে যায়
- Task কোথায় আটকে আছে তা Management বুঝতে পারে না
- Approval process ধীরগতির হয়ে যায়

বাজারের existing software (Zoho, BambooHR, Odoo, Monday.com, ClickUp, Asana) **fixed organizational structure ধরে নিয়ে ডিজাইন করা** — প্রতিটি কোম্পানির hierarchy একরকম না হলেও, software-কে company-র সাথে মানিয়ে নিতে হয়, উল্টোটা না। এবং company grow করলে structure change করা কঠিন।

**মূল সমস্যা:** এমন কোনো সহজলভ্য platform নেই যা company-র নিজস্ব organizational structure অনুযায়ী নিজেকে dynamically সাজিয়ে নেয় — ছোট startup থেকে বড় প্রতিষ্ঠান পর্যন্ত, structure যত জটিলই হোক না কেন।

---

## Proposed Solution

একটি **Multi-Tenant SaaS Web Application** যেখানে প্রতিটি client company নিজের:
- Organizational structure ও hierarchy
- Department ও Designation
- Reporting chain (`reports_to`)
- Approval workflow
- Permission system

...সম্পূর্ণভাবে নিজের মতো করে **Configure** করতে পারবে — কোনো fixed CEO → Manager → Employee কাঠামো system-এ hardcoded থাকবে না।

### গুরুত্বপূর্ণ Design Principle — Designation বনাম Role আলাদা

- **Designation** = পদবি/টাইটেল (যেমন: CEO, Senior Developer, HR Executive) — এটা শুধু পরিচয়/লেবেল
- **Role** = কী কাজ করতে পারবে, তার Permission-এর সেট (যেমন: Department Manager, Approver, Finance Manager)

একজনের Designation "Senior Developer" হতে পারে, কিন্তু তার Role হতে পারে "Team Lead + Approver" — এই দুটো আলাদা রাখার ফলে সিস্টেম অনেক বেশি flexible হয়। **Permission নিজে Role-এর সাথে বাঁধা, আর Role হলো শুধু কিছু নির্দিষ্ট Permission-এর Collection** (যেমন: `create_task`, `approve_leave`, `view_finance`, `manage_users`)। এতে কাউকে নতুন অধিকার দিতে হলে নতুন কোনো hardcoded role বানাতে হবে না — শুধু Permission যোগ/বাদ দিলেই হবে।

### Product Layer Structure (Vision)

| Layer | বিষয়বস্তু | এখনকার Scope |
|---|---|---|
| **Layer 1 — Core Engine** (Ordinis-এর মূল Innovation) | Multi-Tenant SaaS, Dynamic Organization Builder, Dynamic Role & Permission, Workflow/Approval Engine, Action Inbox, Audit Log, Notification, Analytics | ✅ এখনই তৈরি হবে (মূল project) |
| **Layer 2 — Business Modules** | Task Management, Attendance/Leave, Payroll | ✅ এখনই basic version তৈরি হবে (Core Engine demo করার জন্য) |
| **Layer 3 — Extension Ecosystem** (Future Vision) | CRM, Inventory, Asset Management, Meeting, Ticketing, Document Management, AI Assistant, Public API, Mobile App, White Label, Marketplace | ❌ এখন করা হবে না — শুধু ভবিষ্যৎ roadmap হিসেবে উপস্থাপন করা হবে |

---

## Full Workflow

### ১. Company Onboarding (Setup Wizard)
1. **Company Info** — নাম, লোগো, ইন্ডাস্ট্রি, টাইমজোন
2. **Department তৈরি** — HR, Development, Sales, Marketing ইত্যাদি (company যা প্রয়োজন মনে করে)
3. **Designation তৈরি** — CEO, GM, Manager, Developer, HR Executive ইত্যাদি (company-নির্ধারিত)
4. **Hierarchy নির্ধারণ** — প্রতিটি position কার কাছে "Reports To" — এই সম্পর্কটাই পুরো সিস্টেমের ভিত্তি

### ২. Dynamic Organization Engine — একই Software, ভিন্ন Structure Handle করা

**ছোট Startup (মাঝে কোনো লেয়ার নেই):**
```
CEO
├── Developer
├── Designer
└── Sales
```

**মাঝারি Company:**
```
CEO → GM → HR/Dept Head → Employee
```

**বড় Company:**
```
CEO → COO → Regional Manager → Branch Manager → Employee
```

তিনটাই **কোনো code পরিবর্তন ছাড়াই** একই platform handle করবে, কারণ hierarchy database-driven, hardcoded না।

### ৩. Company Grow করলে Structure পরিবর্তন
- CEO যেকোনো সময় নতুন Designation/Department যোগ করতে পারবে
- বিদ্যমান Employee-কে promote/reassign করা যাবে (`reports_to` আপডেট করে)
- আগের historical data (task, attendance record) অক্ষত থাকবে, শুধু বর্তমান access পরিবর্তিত হবে

### ৪. Task/Project Workflow (উদাহরণ)
```
CEO → Project শুরু করলো
  → GM
    → Department Head
      → Developer (Task Assign)
        → Developer কাজ শেষ করে Progress % + File Upload সহ Submit করলো
      → Department Head Review করলো
    → GM Approval দিলো
  → CEO Final Approval দিলো
→ Project Complete (পুরো Timeline Log আকারে সংরক্ষিত থাকবে)
```

### ৫. Approval/Notification Flow (Leave-এর উদাহরণ)
```
Employee → Leave Apply
  → Department Head Notification (প্রথম Approval)
  → HR Notification (চূড়ান্ত Approval)
  → Employee-কে Result Notification
```
*(এই chain company নিজের প্রয়োজন অনুযায়ী কনফিগার করতে পারবে)*

---

## User Roles ও তাদের কাজ

| Role | মূল দায়িত্ব |
|---|---|
| **Super Admin** (আমাদের team) | Client company তৈরি, Subscription/Payment monitor, Company suspend/activate — **এটা কোনো company-র operational role না, প্ল্যাটফর্ম পরিচালনার জন্য** |
| **CEO / Company Owner** | Company structure, department, designation তৈরি; Employee add; Permission assign; Company-wide dashboard ও performance দেখা; Budget/Final approval |
| **GM / Operations Manager** | CEO-র সিদ্ধান্ত execute করা; Department monitor; Team performance দেখা; Department Head-এর রিপোর্ট review |
| **Department Head** | নিজের team-কে task assign; progress monitor ও review; weekly report submit |
| **HR** | Employee onboarding/exit; Leave handle করা; Promotion/Transfer; Document verification; Holiday calendar |
| **Accountant/Finance** *(Optional Role — company-নির্ভর)* | Payroll, Salary Generate, Salary Slip, Expense, Budget, Reimbursement — শুধুমাত্র financial module-এ সীমাবদ্ধ access, অন্য department-এর data দেখতে পারবে না |
| **Employee** | নিজের task দেখা ও আপডেট করা; attendance দেওয়া; leave apply; progress/file submit; notification দেখা |

**লক্ষ্য করার বিষয়:** Admin (Super Admin) বাদে এখানে ৫ ধরনের real stakeholder আছে (CEO, GM/Dept Head, HR, Accountant, Employee) — course requirement (minimum ৩) সহজেই পূরণ হচ্ছে।

### Accountant/Payroll Role কীভাবে "Dynamic" — Company Size অনুযায়ী

এটাই এই platform-এর মূল দর্শনের (Dynamic Organization) সাথে সরাসরি সামঞ্জস্যপূর্ণ — Payroll module সবসময় থাকবে, কিন্তু সেটা পরিচালনা করবে কে, সেটা company নিজে ঠিক করবে:

- **ছোট Startup (আলাদা Accountant নেই):** CEO নিজেই "Accountant" role নিজের একাউন্টে assign রাখবে (অথবা system default ভাবে CEO-কে payroll access দেবে যদি আলাদা কেউ না থাকে) — অর্থাৎ CEO নিজেই salary generate, expense track করবে
- **বড় Company (আলাদা Accountant আছে):** CEO সেই দায়িত্ব একজন নির্দিষ্ট Accountant-কে delegate করবে, এবং তার access শুধু financial module-এ সীমাবদ্ধ থাকবে (অন্য department-এর task/employee data দেখতে পারবে না)

এই flexibility (role optional রাখা, প্রয়োজনে CEO নিজে বা আলাদা কাউকে assign করা) technically সম্ভব হয় কারণ **Payroll module কোনো নির্দিষ্ট hardcoded role-এর সাথে বাঁধা না**, বরং **permission-based** — যার কাছে "Payroll Access" permission আছে, সে-ই সেটা পরিচালনা করতে পারবে, তা CEO হোক বা আলাদা Accountant।

---

## SaaS Business Model

### Multi-Tenancy কীভাবে কাজ করে
```
Ordinis (Super Admin)
  ├── Company A
  ├── Company B
  └── Company C
```
সবাই একই software ব্যবহার করবে, কিন্তু প্রতিটি কোম্পানির data সম্পূর্ণ আলাদা ও সুরক্ষিত (`company_id` দিয়ে isolated) — এক company আরেক company-র কোনো তথ্য কখনো দেখতে পারবে না।

### Subscription Plan (Employee সংখ্যা ভিত্তিক)
| Plan | সুবিধা |
|---|---|
| **Basic** | সর্বোচ্চ ১০ জন Employee, Monthly Subscription |
| **Professional** | সর্বোচ্চ ৫০ জন Employee, Monthly/Yearly |
| **Enterprise** | Unlimited Employee, Yearly-focused |

### Flow
Client Registration → Plan Select → Payment (Monthly/Yearly) → Company Account তৈরি → CEO নিজেই Setup Wizard দিয়ে পুরো Organization নিজে সাজাবে।

---

## Unique / Key Features

1. **Dynamic Organization Builder** — company নিজের structure নিজে তৈরি করে
2. **Dynamic Workflow Engine** — approval process company নিজে configure করতে পারে
3. **Dynamic Permission System** — প্রতিটি role-এর access আলাদা, hierarchy থেকে derive করা
4. **Action Inbox** — Login করলেই শুধু pending/actionable কাজ দেখাবে, অপ্রয়োজনীয় মেনু ঘাঁটতে হবে না
5. **Organization Analytics** — কোন department slow, কোন team overloaded, কোথায় কাজ আটকে আছে — CEO সহজে দেখতে পারবে
6. **Workload Balancer** — কারো task বেশি হয়ে গেলে system suggest করবে অন্য কাউকে assign করতে
7. **Delegation Engine** — Manager ছুটিতে গেলে তার pending approval automatically backup person-এর কাছে চলে যাবে
8. **Company Setup Wizard** — নতুন client সহজে নিজের company সেটআপ করতে পারবে
9. **Audit Log** — প্রতিটি action (login, task create/edit, leave apply, approval, ইত্যাদি) timestamp সহ সংরক্ষিত

---

## Existing Competitors ও তুলনা

| Existing Software | সীমাবদ্ধতা |
|---|---|
| Zoho People / Zoho One | Enterprise-focused, ব্যয়বহুল, structure কিছুটা fixed |
| BambooHR | Local (Bangladesh) market/pricing নেই |
| Odoo / ERPNext | সম্পূর্ণ ERP install করতে হয়, ছোট প্রতিষ্ঠানের জন্য জটিল |
| Monday.com / ClickUp / Asana | মূলত Task/Project management-কেন্দ্রিক, organizational hierarchy ও approval chain এতটা গভীরভাবে handle করে না |
| Jira / Bitrix24 | Software team-কেন্দ্রিক অথবা সাধারণ CRM/collaboration tool, dynamic org-hierarchy এর উপর focus না |

### Why Ordinis is Different
| বর্তমান Software | Ordinis |
|---|---|
| Fixed Structure | Dynamic Organization |
| Fixed Workflow | Dynamic, Configurable Workflow |
| Fixed Permission | Hierarchy-derived Dynamic Permission |
| Company কে Software-এর সাথে মানিয়ে নিতে হয় | Software Company-এর সাথে মানিয়ে নেয় |

---

## Expected Impact & Target Stakeholders

### Target Users
Startup, Software Company, Digital Agency, NGO, SME, Training Institute, School/University Office — যেকোনো ধরনের organization যাদের internal hierarchy ও workflow আছে।

### Impact
- Internal operation সম্পূর্ণভাবে ডিজিটাইজড হবে, বিক্ষিপ্ত tool-নির্ভরতা কমবে
- Chain of command স্পষ্ট ও accountable হবে
- Management-level decision making দ্রুত ও data-driven হবে
- ছোট startup থেকে বড় প্রতিষ্ঠান পর্যন্ত — সবাই নিজের প্রয়োজন অনুযায়ী ব্যবহার করতে পারবে, আলাদা software দরকার হবে না

---

## Future Scope — Layer 3: Extension Ecosystem (এখনই করবে না, শুধু Vision হিসেবে Present করবে)

CRM, Inventory, Asset Management, Meeting Module, Internal Ticketing, Document Management, Knowledge Base, Survey, Performance Review (KPI/OKR), Dynamic Form Builder, Global Search, Theme Builder/White Label, Public API/Webhook, Mobile App, AI Assistant, Company Marketplace (Plugin System), Multi-Branch/Multi-language Support — এগুলো সব **plug-in/extension** হিসেবে ভবিষ্যতে Core Engine-এর উপর ভিত্তি করে যুক্ত করা যাবে। *(Basic Payroll module Layer 2-তে core scope-এই আছে, উপরে দেখুন।)*

**কেন এভাবে বলা হচ্ছে:** Core Engine (Layer 1) যদি সঠিকভাবে dynamic ও extensible করে বানানো হয়, তাহলে এই সব future module প্রায় "plug করে দেওয়া"-র মতো সহজ হয়ে যাবে বড় কোনো re-architecture ছাড়াই — এটাই ভালো System Design-এর প্রমাণ।

---

## CEP (Complex Engineering Problem) Justification

### Knowledge Profile
| Code | ব্যাখ্যা |
|---|---|
| **K3** | Engineering fundamentals — system architecture, database design, SDLC অনুসরণ করে development |
| **K5** | Design knowledge — Dynamic RBAC architecture, self-referencing hierarchy design, multi-tenant system design |
| **K6** | Engineering practice/technology — Django, relational DB, REST API, multi-tenant SaaS deployment |
| **K7** | Engineering-এর সামাজিক ভূমিকা ও নৈতিকতা — Employee activity tracking-এ privacy/ethics বিবেচনা, sensitive data (salary, personal info) সুরক্ষা |

### Range of Complex Engineering Problems
| Code | ব্যাখ্যা |
|---|---|
| **P1** | In-depth knowledge (K3, K5, K6) ছাড়া সমাধান অসম্ভব — dynamic hierarchy থেকে real-time permission calculation একটি fundamentals-based challenge |
| **P2** | Conflicting requirements — Flexibility (company নিজে structure বানাবে) বনাম Security (access leak না হওয়া); CEO-র visibility বনাম Employee-র privacy |
| **P6** | Diverse stakeholders — CEO, GM, Department Head, HR, Employee — প্রত্যেকের ভিন্ন এবং কখনো পরস্পরবিরোধী চাহিদা |

### Range of Complex Engineering Activities
| Code | ব্যাখ্যা |
|---|---|
| **A1** | Diverse resources — মানুষ (বিভিন্ন role), তথ্য (task/attendance data), technology (multi-tenant architecture, notification system) |
| **A2** | একাধিক module-এর (task, approval, notification, delegation) মধ্যে interaction থেকে উদ্ভূত সমস্যা সমাধান ও data consistency বজায় রাখা |
| **A4** | Significant consequence — ভুল access control হলে sensitive data leak হতে পারে; ভুল workflow logic হলে approval আটকে গিয়ে ব্যবসায়িক ক্ষতি হতে পারে — prediction ও mitigation কঠিন |

---

## Instruction Checklist (ম্যামের Requirement অনুযায়ী)

| Required Section | Status |
|---|---|
| Project Title | ✅ |
| Problem Statement | ✅ |
| Proposed Solution | ✅ |
| Key Features | ✅ |
| Novelty & Comparison (≥3 existing solutions) | ✅ (৫টি দেওয়া আছে) |
| Expected Impact & Target Stakeholders | ✅ |
| CEP Justification (K3,K5,K6,K7 / P1,P2,P6 / A1,A2,A4) | ✅ সব কভার করা হয়েছে |
| Minimum 3 Stakeholder (Admin বাদে) | ✅ CEO, GM/Dept Head, HR, Employee |

**মনে রাখবে:** মোট ৩টি proposal presentation করতে হবে (৫ মিনিট করে), এটা একটা। Team-এর সবাইকে অংশ নিতে হবে presentation-এ।
