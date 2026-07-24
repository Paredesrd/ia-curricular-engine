import { useState, useEffect, useRef, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Topbar } from '../components/Layout'
import { createCourse } from '../api/endpoints'

const STEPS = [
  { t: 'Director', d: 'Aplica las reglas de tu colegio' },
  { t: 'Arquitecto', d: 'Diseña módulos, lecciones y Bloom' },
  { t: 'Auditor', d: 'Valida carga cognitiva y restricciones' },
  { t: 'Redactor', d: 'Redacta el contenido final' },
]

export default function NewCoursePage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [topic, setTopic] = useState('')
  const [audience, setAudience] = useState('')
  const [context, setContext] = useState('')
  const [error, setError] = useState('')
  const [phase, setPhase] = useState<'idle' | 'running' | 'done'>('idle')
  const [step, setStep] = useState(0)
  const timer = useRef<number | null>(null)

  useEffect(() => () => { if (timer.current) window.clearInterval(timer.current) }, [])

  const startProgress = () => {
    setStep(0)
    timer.current = window.setInterval(() => {
      setStep(s => (s < STEPS.length - 1 ? s + 1 : s))
    }, 1100)
  }
  const finishProgress = () => {
    if (timer.current) window.clearInterval(timer.current)
    setStep(STEPS.length)
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setPhase('running')
    startProgress()
    try {
      const res = await createCourse({
        topic,
        target_audience: audience || undefined,
        additional_context: context || undefined,
      })
      finishProgress()
      setPhase('done')
      setTimeout(() => navigate(`/courses/${res.id}`), 700)
    } catch (err) {
      if (timer.current) window.clearInterval(timer.current)
      setPhase('idle')
      setError(err instanceof Error ? err.message : 'No se pudo generar el curso')
    }
  }

  if (!user) return null

  return (
    <>
      <Topbar title="Crear curso" crumb="Cursos / Nuevo" user={user} />
      <div className="content">
        <div style={{ display: 'grid', gridTemplateColumns: phase === 'running' ? '1.3fr 1fr' : '1fr', gap: 22 }}>
          <div className="card reveal">
            <h2 className="section-title" style={{ fontSize: 20 }}>¿Qué curso necesitas?</h2>
            <p className="lead" style={{ marginBottom: 20 }}>
              Pon el tema tal como lo darías en clase. El motor se encarga de la estructura pedagógica.
            </p>
            {error && <div className="alert alert-error">{error}</div>}
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Tema del curso <span className="hint">· obligatorio</span></label>
                <input value={topic} onChange={e => setTopic(e.target.value)} placeholder="Diseño de Estructuras de Acero" disabled={phase === 'running'} required />
              </div>
              <div className="form-group">
                <label>Audiencia objetivo <span className="hint">· opcional</span></label>
                <input value={audience} onChange={e => setAudience(e.target.value)} placeholder="Ingenieros civiles con 2+ años de experiencia" disabled={phase === 'running'} />
              </div>
              <div className="form-group">
                <label>Contexto adicional <span className="hint">· opcional</span></label>
                <textarea value={context} onChange={e => setContext(e.target.value)} placeholder="Alinear con la norma E.090 del RNE, incluir estudio de caso por módulo…" disabled={phase === 'running'} />
              </div>
              <button type="submit" className="btn btn-primary" disabled={phase === 'running'}>
                {phase === 'running' ? <><span className="spinner" /> Generando curso…</> : 'Generar curso con IA'}
              </button>
            </form>
          </div>

          {phase === 'running' && (
            <div className="card reveal-2" style={{ alignSelf: 'start' }}>
              <h2 className="section-title">Construyendo tu curso</h2>
              <p className="lead" style={{ marginBottom: 16, fontSize: 13.5 }}>Cuatro agentes trabajan en cadena. Esto tarda unos segundos.</p>
              <div className="gen-steps">
                {STEPS.map((s, i) => (
                  <div key={s.t} className={`gen-step ${step > i ? 'done' : step === i ? 'on' : ''}`}>
                    <span className="dot" />
                    <div>
                      <div className="t">{s.t}</div>
                      <div className="d">{s.d}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}