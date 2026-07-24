import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [tenantSlug, setTenantSlug] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login({ tenant_slug: tenantSlug, username: email, password })
      navigate('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al iniciar sesión')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-aside">
        <div>
          <div className="kicker">IA Curricular Engine</div>
          <h2>Diseño instruccional <em>acreditado</em>, sin ser pedagogo.</h2>
          <p>Tu colegio define las reglas de acreditación. El instructor pone el tema. El motor construye el curso completo.</p>
        </div>
        <div className="marks">
          <span>Multi-colegio</span>
          <span>Taxonomía de Bloom</span>
          <span>Auditoría de calidad</span>
        </div>
      </div>

      <div className="auth-form-side">
        <div className="auth-card reveal">
          <div className="eyebrow">Acceso</div>
          <h1>Iniciar sesión</h1>
          <p className="sub">Entra con las credenciales de tu colegio profesional.</p>
          {error && <div className="alert alert-error">{error}</div>}
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Identificador del colegio (slug)</label>
              <input value={tenantSlug} onChange={e => setTenantSlug(e.target.value)} placeholder="colegio-ingenieros-peru" required />
            </div>
            <div className="form-group">
              <label>Correo electrónico</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="admin@colegio.pe" required />
            </div>
            <div className="form-group">
              <label>Contraseña</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} required />
            </div>
            <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
              {loading ? <><span className="spinner" /> Entrando…</> : 'Iniciar sesión'}
            </button>
          </form>
          <div className="auth-foot">
            ¿Tu colegio aún no está registrado? <Link to="/register">Regístralo aquí</Link>
          </div>
        </div>
      </div>
    </div>
  )
}