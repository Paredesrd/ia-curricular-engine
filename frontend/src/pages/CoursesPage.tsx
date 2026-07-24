import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Topbar } from '../components/Layout'
import { listCourses } from '../api/endpoints'
import { CourseSummary } from '../types'

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' })

export default function CoursesPage() {
  const { user } = useAuth()
  const [courses, setCourses] = useState<CourseSummary[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    listCourses()
      .then(setCourses)
      .catch(e => setError(e instanceof Error ? e.message : 'Error al cargar'))
  }, [])

  if (!user) return null

  return (
    <>
      <Topbar title="Mis cursos" crumb="Cursos" user={user} />
      <div className="content">
        <div className="row-between" style={{ marginBottom: 22 }}>
          <p className="lead">Cursos generados por los miembros de {user.tenant.name}.</p>
          <Link to="/courses/new" className="btn btn-primary">+ Nuevo curso</Link>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {courses === null && !error && (
          <div className="card" style={{ textAlign: 'center', color: 'var(--ink-faint)' }}>Cargando cursos…</div>
        )}

        {courses && courses.length === 0 && (
          <div className="empty reveal">
            <div className="ico">∅</div>
            <h3>Aún no hay cursos</h3>
            <p>Crea el primero: solo necesitas el tema técnico.</p>
            <Link to="/courses/new" className="btn btn-primary">Crear mi primer curso</Link>
          </div>
        )}

        {courses && courses.length > 0 && (
          <div className="grid-cards">
            {courses.map((c, i) => (
              <Link to={`/courses/${c.id}`} className="tile reveal" key={c.id} style={{ animationDelay: `${i * 0.05}s` }}>
                <span className="arrow">↗</span>
                <span className={`badge badge-status-${c.status}`} style={{ marginBottom: 10 }}>{c.status.replace('_', ' ')}</span>
                <h3>{c.topic}</h3>
                {c.target_audience && <p>{c.target_audience}</p>}
                <p style={{ marginTop: 10, fontSize: 12.5, color: 'var(--ink-faint)' }}>{fmtDate(c.created_at)}</p>
              </Link>
            ))}
          </div>
        )}
      </div>
    </>
  )
}