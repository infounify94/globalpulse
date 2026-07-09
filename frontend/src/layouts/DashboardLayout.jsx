import Sidebar from './Sidebar'
import Navbar from './Navbar'

export default function DashboardLayout({ title, subtitle, children }) {
  return (
    <div style={{ display: 'flex', background: '#f8fafc', minHeight: '100vh' }}>
      <Sidebar />
      <div style={{ marginLeft: 220, flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Navbar title={title} subtitle={subtitle} />
        <main style={{ marginTop: 60, padding: '28px', flex: 1 }}>
          {children}
        </main>
      </div>
    </div>
  )
}
