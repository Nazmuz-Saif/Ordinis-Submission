import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
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
import DelegationsPage from './features/approvals/DelegationsPage'
import AttendancePage from './features/attendance/AttendancePage'
import SalaryStructuresPage from './features/payroll/SalaryStructuresPage'


function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          {import.meta.env.DEV && <Route path="/dev/ui-kit" element={<UiKitPage />} />}
          <Route path="/register" element={<RegisterPage />} />
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
            path="/attendance"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <AttendancePage />
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
          <Route path="/" element={<Navigate to="/organization" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
