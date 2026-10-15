import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard, Zap, CloudSun, ShieldAlert,
  BarChart3, FlaskConical, Database, Settings, TrendingUp, Activity,
} from 'lucide-react'
import './Layout.css'

const NAV = [
  { to: '/',            icon: LayoutDashboard, label: 'Overview' },
  { to: '/generation',  icon: Zap,             label: 'Generation' },
  { to: '/weather',     icon: CloudSun,        label: 'Weather & Analytics' },
  { to: '/quality',     icon: Database,        label: 'Data Quality' },
  { to: '/anomalies',   icon: ShieldAlert,     label: 'Anomalies' },
  { to: '/models',      icon: BarChart3,       label: 'Models' },
  { to: '/energy',      icon: Activity,        label: 'Energy Balance' },
  { to: '/scenarios',   icon: FlaskConical,    label: 'Scenario Lab' },
  { to: '/pipeline',    icon: Settings,        label: 'Pipeline' },
]

export default function Layout() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <TrendingUp size={22} color="var(--primary)" />
          <span className="sidebar-title">RE AI Platform</span>
        </div>
        <nav className="sidebar-nav">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon size={17} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="sidebar-version">v1.0.0 · Academic prototype</span>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
