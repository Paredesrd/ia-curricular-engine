import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const Icon = {
  home: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/></svg>,
  book: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 19a2 2 0 0 1 2-2h13"/></svg>,
  plus: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14"/></svg>,
  gear: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 0 1-4 0v-.1A1.6 1.6 0 0 0 7 19.4a1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 2.6 14H2.5a2 2 0 0 1 0-4h.1A1.6 1.6 0 0 0 4.6 7l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.6 1.6 0 0 0 10 4.6V4.5a2 2 0 0 1 4 0v.1A1.6 1.6 0 0 0 17 4.6l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V10a1.6 1.6 0 0 0 1.5 1h.1a2 2 0 0 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z"/></svg>,
  out: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5M21 12H9"/></svg>,
}

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  if (!user) return null
  const initials = user.full_name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()

  const doLogout = () => { logout(); navigate('/login') }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">IC</div>
          <div>
            <div className="brand-name">IA Curricular</div>
            <div className="brand-sub">Engine</div>
          </div>
        </div>

        <div className="tenant-card">
          <div className="lbl">Colegio activo</div>
          <div className="val">{user.tenant.name}</div>
        </div>

        <nav className="nav">
          <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'active' : ''} end>
            {Icon.home} Inicio
          </NavLink>
          <NavLink to="/courses" className={({ isActive }) => isActive ? 'active' : ''} end>
            {Icon.book} Mis Cursos
          </NavLink>
          <NavLink to="/courses/new" className={({ isActive }) => isActive ? 'active' : ''}>
            {Icon.plus} Crear Curso
          </NavLink>
          <NavLink to="/settings" className={({ isActive }) => isActive ? 'active' : ''}>
            {Icon.gear} Reglas del Colegio
          </NavLink>
        </nav>

        <div className="sidebar-foot">
          <button className="logout-btn" onClick={doLogout}>{Icon.out} Cerrar sesión</button>
        </div>
      </aside>

      <div className="main">
        <Outlet />
      </div>

      {/* chip de usuario flotante reutilizable vía contexto de página; se pinta en cada topbar */}
      <span hidden>{initials}</span>
    </div>
  )
}

export function Topbar({ title, crumb, user }: { title: string; crumb?: string; user: { email: string; full_name: string; role: string } }) {
  const initials = user.full_name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
  return (
    <div className="topbar">
      <div>
        {crumb && <div className="crumb">{crumb}</div>}
        <h1>{title}</h1>
      </div>
      <div className="user-chip">
        <div className="meta">
          <div className="em">{user.email}</div>
          <div className="ro">{user.role}</div>
        </div>
        <div className="avatar">{initials}</div>
      </div>
    </div>
  )
}