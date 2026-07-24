import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Topbar } from '../components/Layout'
import { getCourse } from '../api/endpoints'
import { CourseResponse, MatrixLesson, LessonContent } from '../types'

const Arrow = () => <svg className="chev" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M9 6l6 6-6 6"/></svg>

export default function CourseDetailPage() {
  const { user } = useAuth()
  const { id } = useParams()
  const [course, setCourse] = useState<CourseResponse | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    getCourse(id).then(setCourse).catch(e => setError(e instanceof Error ? e.message : 'Error al cargar'))
  }, [id])

  if (!user) return null
  if (error) return <><Topbar title="Curso" user={user} /><div className="content"><div className="alert alert-error">{error}</div></div></>
  if (!course) return <><Topbar title="Curso" user={user} /><div className="content"><div className="card" style={{ textAlign: 'center', color: 'var(--ink-faint)' }}>Cargando curso…</div></div></>

  const matrix = course.course_matrix
  const content = course.course_content
  const contentById: Record<string, LessonContent> = {}
  content?.lessons_content.forEach(lc => { contentById[lc.lesson_id] = lc })

  const totalLessons = matrix?.modules.reduce((a, m) => a + m.lessons.length, 0) ?? 0

  return (
    <>
      <Topbar title={matrix?.course_title ?? course.topic} crumb="Cursos / Detalle" user={user} />
      <div className="content">
        <div className="row-between" style={{ marginBottom: 8 }}>
          <span className={`badge badge-status-${course.status}`}>{course.status.replace('_', ' ')}</span>
          <Link to="/courses" className="btn btn-ghost">← Mis cursos</Link>
        </div>

        <div className="stat-grid reveal">
          <div className="stat"><div className="k">Módulos</div><div className="v">{matrix?.modules.length ?? 0}</div></div>
          <div className="stat"><div className="k">Lecciones</div><div className="v">{totalLessons}</div></div>
          <div className="stat"><div className="k">Horas totales</div><div className="v">{matrix?.total_estimated_hours ?? '—'}</div></div>
        </div>

        {course.target_audience && (
          <p className="lead reveal" style={{ marginBottom: 22 }}><b style={{ color: 'var(--ink)' }}>Audiencia:</b> {course.target_audience}</p>
        )}

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
                      {l.key_topics.map(t => <span className="chip" key={t}>{t}</span>)}
                    </div>

                    {lc && (
                      <>
                        <div className="mini-h">Actividades de aprendizaje</div>
                        <ul className="check-list act-list">
                          {lc.activities.map((a, i) => <li key={i}>{a}</li>)}
                        </ul>

                        <div className="mini-h">Criterios de evaluación</div>
                        <ul className="check-list">
                          {lc.assessment_criteria.map((a, i) => <li key={i}>{a}</li>)}
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