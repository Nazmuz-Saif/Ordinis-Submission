# Ordinis — Frontend Design System (Reference)

Frontend coding শুরু করার সময় এই ফাইল দেখে সরাসরি implement করবে। এটা আমাদের আলোচনার চূড়ান্ত সিদ্ধান্ত।

> **Naming note:** প্রোডাক্টের নাম শুধু **Ordinis**। UI-তে লোগোর পাশে যে "Pro" badge দেখা যায় (নিচের reference screenshot অনুযায়ী), সেটা product-এর নাম না — সেটা **Subscription Plan-এর badge** (কোন company কোন প্ল্যান কিনেছে তা দেখানোর জন্য, যেমন Starter/Growth/Pro/Enterprise)। Sidebar-এ সবসময় `Ordinis` + একটা ছোট plan-badge pill পাশে বসবে, প্রোডাক্টের নাম কখনো "Ordinis Pro" লেখা হবে না।

---

## Design Philosophy

**"Modern Minimalist SaaS"** — Linear/Notion/Vercel Dashboard ঘরানার clean, elegant, professional look। কম রঙ, বেশি whitespace, subtle animation, selective glassmorphism।

**Status update (এই revision-এ):** একটা reference mockup set (Dashboard, Departments, Attendance, Analytics, Audit Logs, Payroll, Projects/Kanban) review করে approve করা হয়েছে — এটাই এখন থেকে **target visual direction**। নিচের পুরো ডকুমেন্ট সেই direction অনুযায়ী update করা হলো। Section "Target Screen Patterns" এবং "Component Reference" — এই দুটো নতুন section-এ ঠিক কী বদলাতে হবে তার বিস্তারিত আছে। এখন পর্যন্ত যা কোড হয়েছে তার অনেক জায়গায় (বিশেষত empty-state placeholder "This module is coming soon") এখনো পুরনো/basic অবস্থায় আছে — সেগুলো এই নতুন spec অনুযায়ী rebuild করতে হবে পরের frontend session-এ।

---

## Delivered status (end of Sprint 5)

The approved mockups are implemented for the screens marked Built. The shared parts named here exist in `frontend/src` (a test checks this document against the code).

| Screen or part | Status | Note |
|---|---|---|
| Shell: grouped collapsible sidebar, top bar, notification bell, user menu | Built | `Sidebar`, `Navbar`, `NotificationBell`; an item is hidden when the user lacks its Permission |
| Plan badge next to the wordmark | Built | `PlanBadge`; shows only what the server sends |
| Shared parts | Built | `MetricCard`, `StatusPill`, `EmptyState`, `ChartCard`, `Pagination` |
| Role dashboards (summary cards, charts) | Built | Sections by Permission (see `ordinis-dashboard-design.md`) |
| Departments, Designations, Employees, Roles | Built | |
| Tasks: Kanban board with four columns, counts, task cards (title, priority, assignee, deadline, progress) | Built | `KanbanPage`. The category tag on a card is not built |
| Attendance: check-in and check-out, today's record | Built | |
| Attendance: monthly calendar and the four summary cards | Not built | ST-137 |
| Leave, Approvals, Delegations, Inbox, Payslips, Salary Structures | Built | |
| Analytics page (metric cards, line and bar charts) | Built | `AnalyticsPage`; a month without attendance shows 0 |
| Audit Logs page | Built | `AuditLogsPage`: table, module filter, export |
| Billing page (plan card, employee usage bar, invoice table) | Built | `BillingPage` |
| Company switcher (more than one company) | Not built | The bar shows the user's own company name |
| Glass look on login, top bar and menus; solid data tables | Built | |

---

## Color Palette

```js
colors: {
  navy: '#14142B',        // Primary text/brand
  violet: {
    DEFAULT: '#6C31D6',   // Main accent (buttons, links, active states, chart lines/bars)
    light: '#A78BFA',     // Hover/highlight
    pale: '#EDE9FE',      // Active sidebar-item background, chip/badge background
  },
  background: '#FAFAFA',  // Page background
  surface: '#FFFFFF',     // Card/panel background
  border: '#EEEEF2',      // Very light border
  muted: '#71717A',       // Secondary text
}
```

### Status/Semantic Colors (শুধু badge/dot/pill-এ ব্যবহার হবে, বড় background-এ না)

| Status | Color | ব্যবহার |
|---|---|---|
| Success/Approved | `#16A34A` | Audit log "Success" pill, positive delta (+2.1%), Present dot |
| Warning/Pending | `#F59E0B` | Audit log "Warning" pill, Leave dot |
| Danger/Rejected | `#DC2626` | Audit log "Failed" pill, negative delta, Absent dot |
| Info/Neutral | `#3B82F6` | Holiday dot, informational badge |

---

## Typography

- **Headings:** Inter অথবা Cambria
- **Body:** Inter / system-ui
- Hierarchy রঙ দিয়ে না, **font size/weight** দিয়ে তৈরি করা হবে
- Metric numbers (dashboard summary card-এর বড় সংখ্যা, যেমন "124", "94.2%") — bold, larger size (text-2xl/3xl), navy রঙে; পাশে ছোট delta pill (`+8 this month` / `+1.2% vs last month`) হালকা background সহ

---

## Glassmorphism — কোথায় ব্যবহার হবে (Selective Approach)

**নীতি:** পুরো UI glass না, শুধু strategic জায়গায়। Data-heavy অংশে (table, list) কখনো glass ব্যবহার হবে না — readability সবচেয়ে গুরুত্বপূর্ণ।

| জায়গা | Glass? |
|---|---|
| Login/Signup Page | ✅ হ্যাঁ — background gradient/mesh + glass card |
| Top Navigation Bar | ✅ হ্যাঁ — হালকা blur, scroll করলে sophisticated লাগে |
| Modal/Dropdown (Notification, quick actions) | ✅ হ্যাঁ — reference-এ Notification dropdown এভাবেই আছে (সাদা card, soft shadow, subtle border) |
| Dashboard Card/Table (Task list, Employee list, Salary) | ❌ না — Solid, high-contrast সাদা background |
| Sidebar | ❌ এই revision-এ **solid, off-white/very-light** (reference mockup-এ সাদা sidebar, dark navy না) — নিচের "Sidebar" section দেখো, আগের plan থেকে বদল |

### CSS Implementation
```css
background: rgba(255, 255, 255, 0.7);
backdrop-filter: blur(12px);
border: 1px solid rgba(255, 255, 255, 0.3);
box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
```
Tailwind: `bg-white/70 backdrop-blur-xl border border-white/30 shadow-lg`

---

## Animation Rules (সব Subtle, Duration 150-300ms)

| জায়গা | Animation | Duration |
|---|---|---|
| Button Hover | Background shift + scale(1.02) | 150ms |
| Card Hover | Shadow elevation বাড়া | 200ms |
| Page/Modal Open | Fade + slide-up (8-10px) | 250ms |
| Sidebar Active Item | Smooth background/border transition (pale violet bg + violet left-border/text) | 150ms |
| Sidebar Group Expand/Collapse (chevron) | Height + chevron-rotate transition | 200ms |
| New Notification | একবার pulse (loop না) — notification bell-এর উপর ছোট violet dot | 400ms |
| Loading State | Skeleton shimmer (grey), spinner না | continuous |

**নিয়ম:** কখনো bounce/spin-এর মতো বড়, flashy animation না — এগুলো "cheap" লাগে, "elegant" না।

---

## Layout Structure — Updated per Reference

- **Sidebar Navigation** (বাম পাশে) + **Content Area** (ডান পাশে, off-white background)
- **Card-based Dashboard Widget** — rounded-xl corner, soft shadow
- **Generous whitespace** — element-এর মাঝে যথেষ্ট spacing

### Sidebar — Revised Spec (আগের "dark navy" plan থেকে বদল)

Reference mockup-এ sidebar **সাদা/off-white background**, dark navy না। এটাই এখন থেকে standard:

- উপরে: violet rounded-square icon + **"Ordinis"** wordmark (bold, navy) + পাশে ছোট rounded pill badge (light violet bg, violet text) — এই badge-এ company-র **current subscription plan**-এর নাম (`Pro`, `Starter`, `Enterprise` ইত্যাদি) দেখাবে। এটা `CompanySettings`/`Subscription` থেকে dynamically আসবে, hardcoded "Pro" টেক্সট না।
- মাঝে: navigation, **গ্রুপ করা, collapsible sections** — flat list না। প্রতিটা group-এর একটা header (icon + label + chevron), ক্লিক করলে expand/collapse:
  - **Dashboard** (standalone, group ছাড়া, home icon)
  - **Organization** ▾ → Departments, Employees
  - **Workflow** ▾ → (Approval Chains ইত্যাদি)
  - **Tasks** ▾ → Projects, My Tasks
  - **Attendance** ▾ → Check In, Leave
  - **Finance** ▾ → Payroll, Expenses
  - **Analytics** (standalone)
  - **Audit Logs** (standalone)
  - **Settings** (standalone)
- Active item: light violet background pill, violet text/icon, rounded
- নিচে (sticky footer): user avatar (initials circle, violet bg) + name + designation (e.g. "Reza Chowdhury" / "CEO") + dropdown chevron — click করলে profile/logout menu

### Top Navbar — Revised Spec

- বাম দিকে: current page title (bold, e.g. "Departments", "Payroll")
- মাঝে: একটা search input (icon + "Search..." placeholder), pill-shaped, light grey background
- ডান দিকে, এই ক্রমে: **Company switcher** (building icon + company name + chevron, e.g. "Acme Corp ▾") → **Notification bell** (unread dot indicator) → **User avatar + name + chevron**
- Notification bell click → dropdown panel: header ("Notifications" + "N new" pill), তারপর প্রতিটা item-এ bold title + muted one-line description + relative timestamp ("2m ago")

### Dashboard Home — Summary Card Row (নতুন pattern)

সব role-এর dashboard home-এ উপরে একটা horizontal row of metric cards (role-অনুযায়ী কয়টা কার্ড আসবে তা ভিন্ন হবে, কিন্তু pattern এক):
- প্রতিটা card: label (muted, small) + বড় bold number/percentage + নিচে ছোট delta pill (হালকা green/red background, "+8 this month" জাতীয় টেক্সট)
- Example (CEO): Total Employees, Departments, Pending Approvals, Active Projects, Attendance Rate
- এর নিচে দুটো বড় card side-by-side: একটা line/area chart (e.g. "Employee Growth — Last 6 months") + একটা donut/breakdown chart (e.g. "By Department")

### Role-wise Density (অপরিবর্তিত)
- **CEO Dashboard** — বেশি widget/data-density, analytics-heavy
- **Employee Dashboard** — Minimal, ৪-৫টা card-এর বেশি না, বড় বাটন/টেক্সট

---

## Target Screen Patterns (Reference Mockup থেকে)

### 1. Attendance Page
- উপরে একটা highlight card: "Today — [day, date]" + "Mark your attendance" heading + বড় **Check In** button (violet, filled) / **Check Out** button (disabled state until checked in) side-by-side + ডান পাশে ছোট stat group (Working Hours, Overtime, Status)
- নিচে row of 4 summary cards: Present, Absent, On Leave, Attendance Rate — প্রতিটাতে একটা ছোট colored circular badge with the number
- তার নিচে একটা calendar-grid month view — প্রতিটা দিনে ছোট colored dot legend (Present=green, Absent=red, Leave=amber, Holiday=violet)

### 2. Projects / Tasks Page — Kanban Board
- উপরে stat pills (Active Projects, Completed, Delayed) + ডান পাশে "+ New Task" primary button
- চারটা column: **To Do / In Progress / Review / Done**, প্রতিটা column header-এ count badge + "+" add button
- প্রতিটা task card-এ: category tag (Finance/Platform/HR — ছোট pill) + priority tag (High=red-ish, Medium=amber, Low=grey, ডান পাশে align), title (bold), progress bar (violet fill), নিচে assignee avatar (initials) + name + deadline date (calendar icon)

### 3. Analytics Page
- উপরে 4-card metric row (Avg Productivity, Turnover Rate, Avg Tenure, NPS Score) — প্রতিটায় delta pill
- নিচে দুটো chart card side-by-side: line chart (trend over months) + grouped bar chart (completed vs pending by department, dual-tone violet — dark bar = completed, light bar = pending)

### 4. Audit Logs Page
- হেডারে title + subtitle ("All system activity — tamper-proof") + ডান পাশে "All Modules" filter dropdown + "Export" button
- একটা clean table: User, Action, Module (pill badge), Date & Time, Status (colored pill: Success=green, Warning=amber, Failed=red)
- এটাই FR-31/NFR-15 (append-only audit log)-এর UI representation — read-only table, কোনো edit/delete action-ই দেখানো হবে না

### 5. Empty/Coming-Soon State (module পুরোপুরি build না হলে)
- Center-aligned: violet-tinted rounded-square icon (layered/stack icon) + bold heading (module name) + muted subtext ("This module is coming soon.")
- এটা শুধু **সত্যিই অসম্পূর্ণ module**-এর জন্য ব্যবহার হবে, খালি ডেটার জন্য না (খালি ডেটার জন্য আলাদা empty-state — "No employees yet, + Add Employee" জাতীয়, action-সহ)

---

## Component Reference (নতুন, কোডিং-এ সরাসরি map করার জন্য)

| Component | Key visual traits |
|---|---|
| `MetricCard` | White card, rounded-xl, soft shadow; label (muted, sm) → big bold value → delta pill |
| `Sidebar` (groups inside it) | Collapsible; icon + label + chevron header; indented child links |
| `NotificationBell` | Glass/white panel, header with unread-count pill, list of (title, description, timestamp) rows |
| `StatusPill` | Rounded-full, small padding, colored bg+text pair per status (never color-only) |
| `KanbanPage` (columns and cards inside it) | Column: header with count; Card: category tag + priority tag + title + progress bar + assignee footer |
| `ChartCard` | White card wrapper, title + subtitle, chart area (violet palette, line/bar/donut per data type) |
| `EmptyState` | Icon + heading + muted subtext, centered; optional CTA button when data-empty (vs module-not-built) |
| `PlanBadge` | Small pill next to "Ordinis" wordmark; text pulled from the company's active Subscription Plan name, not hardcoded |

---

## Technical Stack

- **React (Vite)** — Next.js না (login-gated internal dashboard, SEO দরকার নেই)
- **Tailwind CSS** — বেশিরভাগ styling এবং transition
- **Charting:** line/bar/donut chart-এর জন্য একটা lightweight chart library (e.g. Recharts) — সব চার্টে violet accent palette consistently ব্যবহার হবে
- **Framer Motion** (optional) — যদি বেশি polished animation দরকার হয় (page transition, modal, sidebar group expand)

---

## Reference/Inspiration
- **Linear.app** — সবচেয়ে কাছের reference
- **Notion** — clean, whitespace-heavy
- **Vercel Dashboard** — sidebar + light content area layout inspiration
- **Approved internal mockup set (this revision)** — Dashboard/Departments/Attendance/Analytics/Audit Logs/Payroll/Projects screens; the authoritative target for the next frontend build pass, described in detail above
