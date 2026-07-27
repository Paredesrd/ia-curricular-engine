import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Topbar } from '../components/Layout'
import { getCourse, deleteCourse } from '../api/endpoints'
import {
  CourseResponse,
  MatrixLesson,
  LessonContent,
  QualityReport,
  BloomLevel,
} from '../types'

const Arrow = () => (
  <svg className="chev" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <path d="M9 6l6 6-6 6" />
  </svg>
)

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
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
)

// Paleta sobria con identidad de marca (sin neón ni indigo).
const BLOOM_COLOR: Record<BloomLevel, string> = {
  remember: '#7c8a86',
  understand: '#3f7d76',
  apply: '#c9821f',
  analyze: '#b4541f',
  evaluate: '#8a3b2e',
  create: '#5b6b3a',
}

const BLOOM_LABEL: Record<BloomLevel, string> = {
  remember: 'Recordar',
  understand: 'Comprender',
  apply: 'Aplicar',
  analyze: 'Analizar',
  evaluate: 'Evaluar',
  create: 'Crear',
}

const STATUS_COLOR: Record<string, string> = {
  approved: '#2e7d4f',
  needs_revision: '#c9821f',
  rejected: '#b3261e',
}

const STATUS_LABEL: Record<string, string> = {
  approved: 'Aprobado',
  needs_revision: 'Con observaciones',
  rejected: 'Rechazado',
}

const SEV_COLOR: Record<string, string> = {
  critical: '#b3261e',
  major: '#c9821f',
  minor: '#6b7280',
}

const esc = (s: string) => s.split('&').join('&amp;').split('<').join('&lt;').split('>').join('&gt;')

// Mini-render de markdown a JSX (contenido propio del motor). Jerarquía
// tipográfica fuerte por contraste de tamaño/peso, sin CSS nuevo.
function Markdown({ text }: { text: string }) {
  const lines = text.split('\n')
  const out: JSX.Element[] = []
  let list: string[] = []
  const flushList = (key: number) => {
    if (list.length) {
      out.push(
        <ul key={`ul${key}`} style={{ margin: '6px 0 12px', paddingLeft: 20, lineHeight: 1.6 }}>
          {list.map((li, i) => (
            <li key={i} style={{ marginBottom: 4 }} dangerouslySetInnerHTML={{ __html: inline(li) }} />
          ))}
        </ul>
      )
      list = []
    }
  }
  const inline = (s: string) =>
    esc(s).replace(/\*\*([^*]+)\*\*/g, '<strong style="color:var(--ink)">$1</strong>')

  lines.forEach((raw, i) => {
    const line = raw.replace(/\s+$/, '')
    if (line.startsWith('### ')) {
      flushList(i)
      out.push(
        <h4 key={i} style={{ margin: '14px 0 4px', fontSize: 14.5, fontWeight: 700, color: '#b4541f', letterSpacing: 0.2 }}>
          {line.slice(4)}
        </h4>
      )
    } else if (line.startsWith('## ')) {
      flushList(i)
      out.push(
        <h3 key={i} style={{ margin: '18px 0 6px', fontSize: 17, fontWeight: 800, color: 'var(--ink)' }}>
          {line.slice(3)}
        </h3>
      )
    } else if (line.startsWith('# ')) {
      flushList(i)
      out.push(
        <h2 key={i} style={{ margin: '4px 0 10px', fontSize: 21, fontWeight: 900, color: 'var(--ink)', lineHeight: 1.2 }}>
          {line.slice(2)}
        </h2>
      )
    } else if (line.startsWith('- ')) {
      list.push(line.slice(2))
    } else if (line.trim() === '') {
      flushList(i)
    } else {
      flushList(i)
      out.push(
        <p key={i} style={{ margin: '0 0 10px', lineHeight: 1.7, fontSize: 14.5, color: 'var(--ink)' }} dangerouslySetInnerHTML={{ __html: inline(line) }} />
      )
    }
  })
  flushList(lines.length)
  return <div>{out}</div>
}

function BloomBars({ dist }: { dist: Record<string, number> }) {
  const entries = (Object.keys(BLOOM_LABEL) as BloomLevel[])
    .map((k) => [k, dist[k] || 0] as [BloomLevel, number])
    .filter(([, n]) => n > 0)
  const max = Math.max(1, ...entries.map(([, n]) => n))
  const total = entries.reduce((a, [, n]) => a + n, 0) || 1
  return (
    <div className="card reveal-2" style={{ marginBottom: 22 }}>
      <h2 className="section-title" style={{ fontSize: 18 }}>Distribución cognitiva (Bloom)</h2>
      <p className="lead" style={{ marginBottom: 14, fontSize: 13 }}>
        Cómo se reparten las lecciones entre niveles de pensamiento. Un curso orientado a la acción
        debería cargar el peso en Aplicar / Analizar / Crear.
      </p>
      {entries.map(([k, n], i) => (
        <div key={k} style={{ display: 'grid', gridTemplateColumns: '120px 1fr 64px', alignItems: 'center', gap: 12, marginBottom: 9 }}>
          <span className={`badge bloom bloom-${k}`} style={{ justifySelf: 'start' }}>{BLOOM_LABEL[k]}</span>
          <div style={{ height: 12, background: 'rgba(0,0,0,0.06)', borderRadius: 6, overflow: 'hidden' }}>
            <div
              style={{
                height: '100%',
                width: `${(n / max) * 100}%`,
                background: BLOOM_COLOR[k],
                borderRadius: 6,
                transition: 'width .7s cubic-bezier(.2,.7,.2,1)',
                transitionDelay: `${i * 70}ms`,
              }}
            />
          </div>
          <span style={{ textAlign: 'right', fontSize: 13, color: 'var(--ink-faint)' }}>
            {n} · {Math.round((n / total) * 100)}%
          </span>
        </div>
      ))}
    </div>
  )
}

function AuditPanel({ report }: { report: QualityReport }) {
  const color = STATUS_COLOR[report.status] || '#6b7280'
  return (
    <div className="card reveal" style={{ marginBottom: 22, borderLeft: `4px solid ${color}` }}>
      <div className="row-between" style={{ marginBottom: 10 }}>
        <h2 className="section-title" style={{ fontSize: 18, margin: 0 }}>Auditoría de calidad</h2>
        <span
          style={{
            background: color,
            color: '#fff',
            fontWeight: 800,
            fontSize: 12,
            letterSpacing: 0.4,
            padding: '5px 12px',
            borderRadius: 999,
            textTransform: 'uppercase',
          }}
        >
          {STATUS_LABEL[report.status] || report.status}
        </span>
      </div>
      <p style={{ margin: '0 0 12px', lineHeight: 1.6, fontSize: 14.5, color: 'var(--ink)' }}>{report.summary}</p>
      <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
        <span className="chip">Issues totales: <b style={{ marginLeft: 6 }}>{report.total_issues}</b></span>
        <span className="chip" style={{ borderColor: SEV_COLOR.critical, color: SEV_COLOR.critical }}>
          Críticos: <b style={{ marginLeft: 6 }}>{report.critical_issues}</b>
        </span>
      </div>
      {report.recommendations.length > 0 && (
        <>
          <div className="mini-h">Recomendaciones del auditor</div>
          <ul className="check-list" style={{ marginBottom: 12 }}>
            {report.recommendations.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </>
      )}
      {report.issues.length > 0 && (
        <details style={{ marginTop: 4 }}>
          <summary style={{ cursor: 'pointer', fontWeight: 700, fontSize: 13.5, color: 'var(--ink)' }}>
            Ver detalle de observaciones ({report.issues.length})
          </summary>
          <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 10 }}>
            {report.issues.map((iss) => (
              <div
                key={iss.issue_id}
                style={{
                  border: '1px solid rgba(0,0,0,0.08)',
                  borderLeft: `3px solid ${SEV_COLOR[iss.severity]}`,
                  borderRadius: 8,
                  padding: '10px 12px',
                  background: 'rgba(0,0,0,0.015)',
                }}
              >
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                  <span
                    style={{
                      background: SEV_COLOR[iss.severity],
                      color: '#fff',
                      fontSize: 10.5,
                      fontWeight: 800,
                      padding: '2px 8px',
                      borderRadius: 999,
                      textTransform: 'uppercase',
                      letterSpacing: 0.4,
                    }}
                  >
                    {iss.severity}
                  </span>
                  <span style={{ fontSize: 12, color: 'var(--ink-faint)', fontFamily: 'ui-monospace, monospace' }}>{iss.component}</span>
                </div>
                <div style={{ fontSize: 14, color: 'var(--ink)', lineHeight: 1.5 }}>{iss.description}</div>
                <div style={{ fontSize: 13, color: 'var(--ink-faint)', marginTop: 4 }}>↳ {iss.suggestion}</div>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  )
}

export default function CourseDetailPage() {
  const { user } = useAuth()
  const { id } = useParams()
  const navigate = useNavigate()
  const [course, setCourse] = useState<CourseResponse | null>(null)
  const [error, setError] = useState('')

  // Borrado: confirmación inline (sin window.confirm) + estado de trabajo.
  const [confirming, setConfirming] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [hoverDel, setHoverDel] = useState(false)

  useEffect(() => {
    if (!id) return
    getCourse(id).then(setCourse).catch((e) => setError(e instanceof Error ? e.message : 'Error al cargar'))
  }, [id])

  const askDelete = () => { setError(''); setConfirming(true) }
  const cancelDelete = () => setConfirming(false)
  const confirmDelete = async () => {
    if (!id) return
    setConfirming(false)
    setDeleting(true)
    setError('')
    try {
      await deleteCourse(id) // 204 sin cuerpo; el cliente blindado lo tolera.
      navigate('/courses')
    } catch (err) {
      setDeleting(false)
      setError(err instanceof Error ? err.message : 'No se pudo eliminar el curso')
    }
  }

  if (!user) return null
  if (error && !deleting)
    return (
      <>
        <Topbar title="Curso" user={user} />
        <div className="content">
          <div className="alert alert-error">{error}</div>
        </div>
      </>
    )
  if (!course)
    return (
      <>
        <Topbar title="Curso" user={user} />
        <div className="content">
          <div className="card" style={{ textAlign: 'center', color: 'var(--ink-faint)' }}>Cargando curso…</div>
        </div>
      </>
    )

  const matrix = course.course_matrix
  const content = course.course_content
  const report = course.quality_report
  const contentById: Record<string, LessonContent> = {}
  content?.lessons_content.forEach((lc) => {
    contentById[lc.lesson_id] = lc
  })
  const totalLessons = matrix?.modules.reduce((a, m) => a + m.lessons.length, 0) ?? 0

  const trashStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 7,
    height: 38,
    padding: '0 13px',
    borderRadius: 'var(--radius-sm)',
    border: `1px solid ${hoverDel ? 'var(--danger)' : 'var(--line-strong)'}`,
    background: hoverDel ? 'var(--danger-soft)' : 'var(--surface)',
    color: hoverDel ? 'var(--danger)' : 'var(--ink-faint)',
    cursor: deleting ? 'not-allowed' : 'pointer',
    fontFamily: 'var(--body)',
    fontWeight: 600,
    fontSize: 13.5,
    transition: 'background .15s, color .15s, border-color .15s, transform .15s',
    transform: hoverDel && !deleting ? 'translateY(-1px)' : 'none',
    opacity: deleting ? 0.6 : 1,
  }

  return (
    <>
      <Topbar title={matrix?.course_title ?? course.topic} crumb="Cursos / Detalle" user={user} />
      <div className="content">
        <div className="row-between" style={{ marginBottom: 8 }}>
          <span className={`badge badge-status-${course.status}`}>{course.status.replace('_', ' ')}</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button
              type="button"
              aria-label="Eliminar curso"
              title="Eliminar curso"
              style={trashStyle}
              disabled={deleting}
              onMouseEnter={() => setHoverDel(true)}
              onMouseLeave={() => setHoverDel(false)}
              onClick={askDelete}
            >
              {deleting ? <span className="spinner spinner-dark" style={{ width: 14, height: 14 }} /> : <TrashIcon />}
              {deleting ? 'Eliminando…' : 'Eliminar'}
            </button>
            <Link to="/courses" className="btn btn-ghost">← Mis cursos</Link>
          </div>
        </div>

        {/* Confirmación inline de borrado (animada, sin modal genérico) */}
        {confirming && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              flexWrap: 'wrap',
              margin: '0 0 18px',
              padding: '14px 16px',
              border: '1px solid var(--danger-soft)',
              borderLeft: '4px solid var(--danger)',
              borderRadius: 'var(--radius)',
              background: 'linear-gradient(90deg, var(--danger-soft), var(--surface))',
              animation: 'popIn .16s ease',
            }}
          >
            <span style={{ color: 'var(--danger)', display: 'inline-flex' }}><WarnIcon /></span>
            <div style={{ flex: 1, minWidth: 200 }}>
              <div style={{ fontFamily: 'var(--display)', fontWeight: 800, fontSize: 15, color: 'var(--ink)' }}>
                ¿Eliminar este curso?
              </div>
              <div style={{ fontSize: 13, color: 'var(--ink-soft)', lineHeight: 1.5 }}>
                Se borrará de forma permanente, con su matriz y contenido. No se puede deshacer.
              </div>
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <button type="button" className="btn btn-ghost" style={{ padding: '8px 15px', fontSize: 13 }} onClick={cancelDelete}>
                Cancelar
              </button>
              <button
                type="button"
                className="btn"
                style={{ padding: '8px 15px', fontSize: 13, background: 'var(--danger)', color: '#fff', boxShadow: '0 6px 16px rgba(210,59,59,.28)' }}
                onClick={confirmDelete}
              >
                Sí, eliminar
              </button>
            </div>
          </div>
        )}

        <div className="stat-grid reveal">
          <div className="stat"><div className="k">Módulos</div><div className="v">{matrix?.modules.length ?? 0}</div></div>
          <div className="stat"><div className="k">Lecciones</div><div className="v">{totalLessons}</div></div>
          <div className="stat"><div className="k">Horas totales</div><div className="v">{matrix?.total_estimated_hours ?? '—'}</div></div>
        </div>

        {course.target_audience && (
          <p className="lead reveal" style={{ marginBottom: 22 }}>
            <b style={{ color: 'var(--ink)' }}>Audiencia:</b> {course.target_audience}
          </p>
        )}

        {report && <AuditPanel report={report} />}
        {matrix?.bloom_distribution && <BloomBars dist={matrix.bloom_distribution} />}

        {matrix?.modules.map((m, mi) => (
          <div className="module reveal" key={m.module_id} style={{ animationDelay: `${mi * 0.05}s` }}>
            <div className="module-head">
              <div className="module-num">{String(mi + 1).padStart(2, '0')}</div>
              <div style={{ flex: 1 }}>
                <h3>{m.title}</h3>
                <div className="mdesc">{m.description}</div>
              </div>
              <div className="mhours">{m.estimated_hours} h</div>
            </div>
            {m.lessons.map((l: MatrixLesson) => {
              const lc = contentById[l.lesson_id]
              return (
                <details className="lesson" key={l.lesson_id}>
                  <summary>
                    <span className="lid">{l.lesson_id}</span>
                    <span className={`badge bloom bloom-${l.bloom_level}`}>{l.bloom_level}</span>
                    <span className="ltitle">{l.title}</span>
                    <span className="lhours">{l.estimated_hours} h</span>
                    <Arrow />
                  </summary>
                  <div className="lesson-body">
                    <div className="obj"><b>Objetivo:</b> {l.learning_objective}</div>
                    <div className="mini-h">Temas clave</div>
                    <div className="chip-list">
                      {l.key_topics.map((t) => (
                        <span className="chip" key={t}>{t}</span>
                      ))}
                    </div>

                    {lc && (
                      <>
                        <details open style={{ marginTop: 12 }}>
                          <summary style={{ cursor: 'pointer', fontWeight: 800, fontSize: 14, color: 'var(--ink)' }}>
                            Contenido completo de la lección
                          </summary>
                          <div
                            style={{
                              marginTop: 8,
                              padding: '12px 14px',
                              border: '1px solid rgba(0,0,0,0.08)',
                              borderRadius: 10,
                              background: 'rgba(0,0,0,0.015)',
                            }}
                          >
                            <Markdown text={lc.full_content} />
                          </div>
                        </details>

                        <div className="mini-h" style={{ marginTop: 14 }}>Actividades de aprendizaje</div>
                        <ul className="check-list act-list">
                          {lc.activities.map((a, i) => (
                            <li key={i}>{a}</li>
                          ))}
                        </ul>
                        <div className="mini-h">Criterios de evaluación</div>
                        <ul className="check-list">
                          {lc.assessment_criteria.map((a, i) => (
                            <li key={i}>{a}</li>
                          ))}
                        </ul>
                      </>
                    )}
                  </div>
                </details>
              )
            })}
          </div>
        ))}
      </div>
    </>
  )
}