# Ordinis — Future Roadmap (Full Vision, All Layers)

> **Future roadmap.** Layers 3, 4 and 5 below are not built. The delivered system is Layer 1 and Layer 2 as listed in `Ordinis_SRS.md` Section 7.2; part of Layer 1 and 2 is still future work too: the Audit Log, Analytics, Billing enforcement, Projects, Expense and Reimbursement, and multi-factor authentication.

এই ফাইলে Ordinis-এর সম্পূর্ণ ভবিষ্যৎ পরিকল্পনা — বর্তমান course-scope (Layer 1+2) থেকে শুরু করে দূরবর্তী commercial vision পর্যন্ত। `docs/roadmap.md` হিসেবে repo-তে রাখো।

---

## এখন পর্যন্ত যা Planned/Built (Reference)

- **Layer 1 — Core Engine:** Multi-tenant SaaS, Dynamic Organization Builder, Permission-Based RBAC, Workflow/Approval Engine, Action Inbox, Notification, Audit Log, Analytics
- **Layer 2 — Business Modules:** Task/Project Management, Attendance & Leave, Payroll (optional)

*(এই দুই layer-এর detailed schema/structure আগের `ordinis-project-structure.md` এবং `ordinis-full-ER-diagram.md` ফাইলে আছে)*

---

## Layer 3 — Extension Ecosystem (পরবর্তী ধাপ, Core স্থিতিশীল হওয়ার পর)

| Module | মূল কাজ | Access/Note |
|---|---|---|
| **Meeting Management** | Meeting schedule, agenda, participant, RSVP, minutes, action items → task-এ convert | নিজস্ব video call না, Zoom/Google Meet link coordinate করবে |
| **Announcement System** | Company-wide/department/role-specific broadcast, read-tracking | CEO/HR প্রধানত, delegate করা যাবে |
| **Internal Ticketing** | Employee → IT/HR/Accounts এর কাছে ticket তোলা, resolution track | Department-routing logic লাগবে |
| **Asset Management** | Laptop, phone, ID card ইত্যাদি কোম্পানির সম্পদ track করা, কার কাছে কী আছে | HR/Admin scope |
| **Document Management** | Offer letter, NDA, contract, payslip — versioned storage | Sensitive data, strict permission দরকার |
| **Knowledge Base/Wiki** | SOP, policy, guideline লেখা ও রাখা | Company-wide পড়া, HR/Admin লেখা |
| **Performance Review** | KPI, OKR, quarterly/360-degree review | Sensitive, hierarchy-based visibility |
| **Survey Module** | HR সার্ভে বানাবে, employee response দেবে | Anonymous option থাকা উচিত |
| **Visitor Management** | Reception check-in/out, QR-based | ছোট, isolated module |
| **Dynamic Form Builder** | Company নিজের custom form বানাবে (leave form-এ company-specific field) | জটিল, schema-driven UI দরকার |
| **Custom Fields** | Employee/Task-এ company-specific extra field যোগ করা | Metadata-driven design দরকার |

---

## Layer 4 — Intelligence & Automation (Layer 3-এর পরে)

| Feature | বিবরণ |
|---|---|
| **AI Task Assistant** | Task description থেকে auto-suggest priority/deadline/assignee |
| **Workload Prediction** | কার overload হওয়ার সম্ভাবনা আছে, আগে থেকে alert |
| **Attrition Risk Signal** | Attendance/task pattern দেখে কর্মী unhappy কিনা আন্দাজ করা (careful — ethics/privacy বিবেচনা জরুরি) |
| **Smart Approval Routing** | Historical pattern দেখে approval-কে দ্রুততম সঠিক ব্যক্তির কাছে route করা |
| **Natural Language Reporting** | "গত মাসে কোন department সবচেয়ে ভালো করেছে?" — চ্যাট আকারে জিজ্ঞেস করলে answer |
| **Anomaly Detection** | অস্বাভাবিক attendance/expense pattern flag করা (fraud prevention) |

*(এই পুরো Layer-টা architecture-ready রাখা হবে আগে থেকেই — মানে ডেটা model এমনভাবে বানানো হবে যাতে AI feature পরে সহজে বসানো যায়, কিন্তু এখনই AI বানানো হবে না)*

---

## Layer 5 — Platform & Ecosystem Expansion

| Feature | বিবরণ |
|---|---|
| **Public REST API + Webhooks** | Third-party developer নিজের tool দিয়ে Ordinis-এর সাথে integrate করতে পারবে |
| **Plugin Marketplace** | CRM, Inventory, POS ইত্যাদি module আলাদা কোম্পানি/developer বানিয়ে বিক্রি করতে পারবে |
| **Third-Party Integration** | Google Workspace, Microsoft 365, Slack-এর সাথে connect (calendar sync, email sync) |
| **White-Label / Custom Domain** | Enterprise client নিজের logo/domain দিয়ে ব্যবহার করতে পারবে |
| **Mobile App (Flutter)** | একই REST API ব্যবহার করে Android/iOS app |
| **Multi-Branch/Workspace** | একই কোম্পানির একাধিক office location আলাদা workspace হিসেবে |
| **Multi-Language Support** | English, Bangla দিয়ে শুরু, পরে বাড়ানো যাবে |
| **Global Search (Ctrl+K)** | পুরো platform জুড়ে দ্রুত খোঁজার সুবিধা |

---

## Business/Go-To-Market Roadmap (Product Layer-এর বাইরের কাজ)

| ধাপ | কী করতে হবে |
|---|---|
| **Beta Phase** | ২-৩টা ছোট real company-কে বিনামূল্যে ব্যবহার করতে দিয়ে feedback নেওয়া |
| **Pricing Finalize** | Starter/Growth/Enterprise প্ল্যানের প্রকৃত দাম বাজার-গবেষণা করে ঠিক করা |
| **Payment Gateway Integration** | SSLCommerz/bKash সরাসরি যুক্ত করা (এখন শুধু architecture-এ আছে) |
| **Legal/Compliance** | Terms of Service, Privacy Policy, Bangladesh Data Protection বিবেচনা |
| **Marketing Site** | Nexoria website-এর মতো landing page বানানো (ইতিমধ্যে Nexoria stack pattern familiar) |
| **Customer Support System** | Support ticket/live chat (নিজেদের Ticketing module-ই ব্যবহার করা যায়) |

---

## সম্পূর্ণ Timeline Overview (Priority Order)

```
এখন (Course Project)
  └── Layer 1 (Core Engine) + Layer 2 (Task/Attendance/Payroll)

পরবর্তী ধাপ (Post-course, Nexoria product হিসেবে যদি চালিয়ে যাও)
  ├── Layer 3 (Meeting, Announcement, Ticketing, Document, ইত্যাদি)
  ├── Business/Go-To-Market কাজ (Beta client, pricing, legal)
  └── Layer 4 (AI Intelligence Layer) — client feedback অনুযায়ী প্রয়োজন হলে

দূরবর্তী ভবিষ্যৎ
  └── Layer 5 (Marketplace, White-label, Mobile App, Public API)
```

---

## গুরুত্বপূর্ণ Reminder

- Course presentation/report-এ **শুধু Layer 1+2** "current scope" হিসেবে দেখাবে, বাকি সব "Future Vision/Roadmap" হিসেবে এক স্লাইডে সংক্ষেপে উল্লেখ করবে
- প্রতিটা নতুন Layer শুরু করার আগে আগের Layer পুরোপুরি stable/tested হওয়া জরুরি — scope creep এড়ানোই সবচেয়ে বড় challenge হবে বাস্তবে
- Layer 4 (AI)-এর ক্ষেত্রে বিশেষভাবে সতর্ক থাকতে হবে — employee monitoring/prediction feature নিয়ে ethical বিবেচনা (privacy, consent) থেকেই design করা উচিত
