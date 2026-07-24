import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const slugify = (v: string) =>
  v.toLowerCase().trim().replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-').replace(/-+/g, '-')

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [tenantName, setTenantName] = useState('')
  const [tenantSlug, setTenantSlug] = useState('')
  const [slugTouched, setSlugTouched] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  const onName = (v: string) => {
    setTenantName(v)
    if (!slugTouched) setTenantSlug(slugify(v))
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(''); setSuccess('')
    setLoading(true)
    try {
      await register({ tenant_name: tenantName, tenant_slug: tenantSlug, email, password, full_name: fullName })
      setSuccess('Colegio registrado. Redirigiendo al inicio de sesión…')
      setTimeout(() => navigate('/login'), 1200)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al registrar')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-aside">
        <div>
          <div className="kicker">Nuevo colegio</div>
          <h2>Funda tu colegio y <em>configura</em> sus reglas.</h2>
          <p>Quien registra el colegio se convierte en su administrador. Después podrás ajustar horas, niveles de Bloom y restricciones.</p>
        </div>
        <div className="marks">
          <span>Admin fundador</span>
          <span>Reglas editables</span>
          <span>Aislamiento por colegio</span>
        </div>
      </div>

      <div className="auth-form-side">
        <div className="auth-card reveal">
          <div className="eyebrow">Alta</div>
          <h1>Registrar colegio</h1>
          <p className="sub">Crea la institución y tu cuenta de administrador.</p>
          {error && <div className="alert alert-error">{error}</div>}
          {success && <div className="alert alert-success">{success}</div>}
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Nombre del colegio</label>
              <input value={tenantName} onChange={e => onName(e.target.value)} placeholder="Colegio de Ingenieros del Perú" required />
            </div>
            <div className="form-group">
              <label>Identificador único (slug) <span className="hint">· minúsculas y guiones</span></label>
              <input value={tenantSlug} onChange={e => { setTenantSlug(slugify(e.target.value)); setSlugTouched(true) }} placeholder="colegio-ingenieros-peru" required />
            </div>
            <div className="form-group">
              <label>Tu nombre completo</label>
              <input value={fullName} onChange={e => setFullName(e.target.value)} placeholder="Ana Administradora" required />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Correo</label>
                <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="admin@colegio.pe" required />
              </div>
              <div className="form-group">
                <label>Contraseña <span className="hint">· 8+</span></label>
                <input type="password" value={password} onChange={e => setPassword(e.target.value)} minLength={8} required />
              </div>
            </div>
            <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
              {loading ? <><span className="spinner" /> Registrando…</> : 'Registrar colegio'}
            </button>
          </form>
          <div className="auth-foot">
            ¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link>
          </div>
        </div>
      </div>
    </div>
  )
}