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

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
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
          <Route path="/" element={<Navigate to="/organization" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App