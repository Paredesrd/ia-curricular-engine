import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Topbar } from '../components/Layout'
import { listCourses, deleteCourse } from '../api/endpoints'
import { CourseSummary } from '../types'

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' })

const TrashIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <path d="M3 6h18" />
    <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
    <path d="M10 11v6" />
    <path d="M14 11v6" />
  </svg>
)

const WarnIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
)

export default function CoursesPage() {
  const { user } = useAuth()
  const [courses, setCourses] = useState<CourseSummary[] | null>(null)
  const [error, setError] = useState('')

  // Estado de borrado por tarjeta (confirmación inline, sin window.confirm).
  const [confirmingId, setConfirmingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  // Hover por estado para los controles que no pueden usar :hover en inline.
  const [hoverDel, setHoverDel] = useState<string | null>(null)
  const [hoverYes, setHoverYes] = useState<string | null>(null)

  const load = () =>
    listCourses()
      .then(setCourses)
      .catch((e) => setError(e instanceof Error ? e.message : 'Error al cargar'))

  useEffect(() => { load() }, [])

  const askDelete = (id: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setError('')
    setConfirmingId(id)
  }
  const cancelDelete = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setConfirmingId(null)
  }
  const confirmDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setConfirmingId(null)
    setDeletingId(id)
    setError('')
    try {
      await deleteCourse(id) // 204 sin cuerpo; el cliente blindado lo tolera.
      setCourses((cs) => (cs ? cs.filter((c) => c.id !== id) : cs))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo eliminar el curso')
    } finally {
      setDeletingId(null)
    }
  }

  if (!user) return null

  const overlayStyle: React.CSSProperties = {
    position: 'absolute',
    inset: 0,
    zIndex: 3,
    background: 'rgba(255,255,255,.97)',
    backdropFilter: 'blur(2px)',
    borderRadius: 'var(--radius)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    padding: 20,
    textAlign: 'center',
    animation: 'popIn .16s ease',
    pointerEvents: 'auto',
  }

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
            {courses.map((c, i) => {
              const delHover = hoverDel === c.id
              const yesHover = hoverYes === c.id
              const busy = deletingId === c.id
              const trashStyle: React.CSSProperties = {
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 30,
                height: 30,
                borderRadius: 8,
                border: `1px solid ${delHover ? 'var(--danger)' : 'var(--line-strong)'}`,
                background: delHover ? 'var(--danger-soft)' : 'var(--surface)',
                color: delHover ? 'var(--danger)' : 'var(--ink-faint)',
                cursor: 'pointer',
                transition: 'background .15s, color .15s, border-color .15s, transform .15s',
                transform: delHover ? 'translateY(-1px)' : 'none',
              }
              const yesStyle: React.CSSProperties = {
                display: 'inline-flex',
                alignItems: 'center',
                gap: 7,
                padding: '8px 15px',
                borderRadius: 9,
                border: 'none',
                background: yesHover ? '#b3261e' : 'var(--danger)',
                color: '#fff',
                fontWeight: 700,
                fontSize: 13,
                cursor: 'pointer',
                transition: 'background .15s, transform .15s',
                transform: yesHover ? 'translateY(-1px)' : 'none',
              }
              return (
                <div
                  className="tile reveal"
                  key={c.id}
                  style={{ position: 'relative', animationDelay: `${i * 0.05}s` }}
                >
                  {/* Capa clicable de fondo: abre el curso */}
                  <Link
                    to={`/courses/${c.id}`}
                    aria-label={`Abrir curso ${c.topic}`}
                    style={{ position: 'absolute', inset: 0, zIndex: 1 }}
                  />

                  {/* Acción: eliminar (encima de la capa clicable) */}
                  <div style={{ position: 'absolute', top: 14, right: 14, zIndex: 2 }}>
                    <button
                      type="button"
                      aria-label="Eliminar curso"
                      title="Eliminar curso"
                      style={trashStyle}
                      onMouseEnter={() => setHoverDel(c.id)}
                      onMouseLeave={() => setHoverDel((h) => (h === c.id ? null : h))}
                      onClick={(e) => askDelete(c.id, e)}
                    >
                      <TrashIcon />
                    </button>
                  </div>

                  {/* Contenido (no captura clics: caen a la capa de fondo) */}
                  <div style={{ position: 'relative', zIndex: 1, pointerEvents: 'none' }}>
                    <span className={`badge badge-status-${c.status}`} style={{ marginBottom: 10 }}>
                      {c.status.replace('_', ' ')}
                    </span>
                    <h3 style={{ paddingRight: 40 }}>{c.topic}</h3>
                    {c.target_audience && <p>{c.target_audience}</p>}
                    <p style={{ marginTop: 10, fontSize: 12.5, color: 'var(--ink-faint)' }}>
                      {fmtDate(c.created_at)}
                    </p>
                  </div>

                  {/* Overlay: confirmar borrado */}
                  {confirmingId === c.id && (
                    <div style={overlayStyle}>
                      <div style={{ color: 'var(--danger)' }}><WarnIcon /></div>
                      <div style={{ fontFamily: 'var(--display)', fontWeight: 800, fontSize: 16, color: 'var(--ink)' }}>
                        ¿Eliminar este curso?
                      </div>
                      <div style={{ fontSize: 13, color: 'var(--ink-soft)', maxWidth: '30ch', lineHeight: 1.5 }}>
                        Se borrará de forma permanente y no se podrá deshacer.
                      </div>
                      <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
                        <button type="button" className="btn btn-ghost" style={{ padding: '8px 15px', fontSize: 13 }} onClick={cancelDelete}>
                          Cancelar
                        </button>
                        <button
                          type="button"
                          style={yesStyle}
                          onMouseEnter={() => setHoverYes(c.id)}
                          onMouseLeave={() => setHoverYes((h) => (h === c.id ? null : h))}
                          onClick={(e) => confirmDelete(c.id, e)}
                        >
                          Sí, eliminar
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Overlay: eliminando */}
                  {busy && (
                    <div style={overlayStyle}>
                      <span className="spinner spinner-dark" />
                      <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--ink-soft)' }}>Eliminando…</div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </>
  )
}