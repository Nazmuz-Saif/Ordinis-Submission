import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import ActionInboxPage from './features/inbox/ActionInboxPage'
import LoginPage from './features/auth/LoginPage'
import RegisterPage from './features/auth/RegisterPage'
import ProtectedRoute from './routes/ProtectedRoute'
import { AuthProvider } from './store/AuthContext'
import DashboardLayout from './layouts/DashboardLayout'
import DepartmentsPage from './features/organization/DepartmentsPage'
import DesignationsPage from './features/organization/DesignationsPage'
import EmployeesPage from './features/organization/EmployeesPage'
import EmployeeDetailPage from './features/organization/EmployeeDetailPage'
import RolesPage from './features/roles/RolesPage'
import ApprovalChainsPage from './features/approvals/ApprovalChainsPage'
import PendingApprovalsPage from './features/approvals/PendingApprovalsPage'
import UiKitPage from './features/dev/UiKitPage'
import TasksPage from './features/tasks/TasksPage'
import KanbanPage from './features/tasks/KanbanPage'
import DelegationsPage from './features/approvals/DelegationsPage'
import SalaryStructuresPage from './features/payroll/SalaryStructuresPage'
import AttendancePage from './features/attendance/AttendancePage'
import SupportAccessPage from './features/platformAdmin/SupportAccessPage'
import AdminRoute from './routes/AdminRoute'
import HomeRedirect from './routes/HomeRedirect'
import CompaniesPage from './features/admin/CompaniesPage'
import TicketsPage from './features/admin/TicketsPage'
import AccessRequestsPage from './features/admin/AccessRequestsPage'
import ActivityPage from './features/admin/ActivityPage'
// The dashboard pulls in the chart library, so it loads only when opened.
const DashboardPage = lazy(() => import('./features/dashboard/DashboardPage'))

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          {import.meta.env.DEV && <Route path="/dev/ui-kit" element={<UiKitPage />} />}
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <HomeRedirect>
                    <Suspense fallback={null}>
                      <DashboardPage />
                    </Suspense>
                  </HomeRedirect>
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/organization"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <DepartmentsPage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/organization/designations"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <DesignationsPage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/organization/employees"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <EmployeesPage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/organization/employees/:id"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <EmployeeDetailPage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/roles"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <RolesPage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/roles/employee-roles"
            element={<Navigate to="/roles" replace />}
          />
          <Route
            path="/tasks/board"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <KanbanPage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/tasks"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <TasksPage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/approvals/delegations"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <DelegationsPage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/payroll/salary-structures"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <SalaryStructuresPage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/attendance"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <AttendancePage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          {[
            ['/admin/companies', CompaniesPage],
            ['/admin/tickets', TicketsPage],
            ['/admin/access-requests', AccessRequestsPage],
            ['/admin/activity', ActivityPage],
          ].map(([path, Page]) => (
            <Route
              key={path}
              path={path}
              element={
                <ProtectedRoute>
                  <DashboardLayout>
                    <AdminRoute>
                      <Page />
                    </AdminRoute>
                  </DashboardLayout>
                </ProtectedRoute>
              }
            />
          ))}
          <Route
            path="/settings/support-access"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <SupportAccessPage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/approvals/pending"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <PendingApprovalsPage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/approvals/chains"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <ApprovalChainsPage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/inbox"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <ActionInboxPage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App