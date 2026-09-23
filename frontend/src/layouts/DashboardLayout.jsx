import Sidebar from '../components/layout/Sidebar'
import Navbar from '../components/layout/Navbar'

function DashboardLayout({ children }) {
  return (
    <div className="flex">
      <Sidebar />
      <div
        className="flex-1 min-h-screen"
        style={{
          background: 'linear-gradient(135deg, #F1EEFB 0%, #FAFAFA 40%, #FAFAFA 100%)',
        }}
      >
        <Navbar />
        <main className="p-6">{children}</main>
      </div>
    </div>
  )
}

export default DashboardLayout