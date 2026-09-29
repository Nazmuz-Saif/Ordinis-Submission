import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './features/auth/LoginPage'
import ProtectedRoute from './routes/ProtectedRoute'
import { AuthProvider } from './store/AuthContext'
import DashboardLayout from './layouts/DashboardLayout'
import DepartmentsPage from './features/organization/DepartmentsPage'
import DesignationsPage from './features/organization/DesignationsPage'
import EmployeesPage from './features/organization/EmployeesPage'
import RolesPage from './features/roles/RolesPage'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
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
            path="/roles"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <RolesPage />
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