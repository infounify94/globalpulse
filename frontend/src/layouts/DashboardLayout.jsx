import Sidebar from './Sidebar'
import Navbar from './Navbar'

export default function DashboardLayout({ title, subtitle, children }) {
  return (
    <div style={{ display: 'flex', background: 'var(--color-bg)', minHeight: '100vh', position: 'relative' }}>
      <Sidebar />
      <div style={{ marginLeft: 220, flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Navbar title={title} subtitle={subtitle} />
        <main style={{ marginTop: 60, padding: '28px', flex: 1, zIndex: 1 }}>
          {children}
        </main>
      </div>
    </div>
  )
}
