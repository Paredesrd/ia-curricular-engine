import { useState, useRef, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Topbar } from '../components/Layout'
import { createCourse, intakeTurn } from '../api/endpoints'
import { IntakeResponse, IntakeTurn, EnrichedInstructorInput } from '../types'
import {
  INTAKE_FIELDS,
  coachField,
  computeScore,
  adviceColor,
  metaByKey,
} from '../lib/fieldCoaching'

const STEPS = [
  { t: 'Director', d: 'Aplica las reglas de tu colegio' },
  { t: 'Arquitecto', d: 'Diseña módulos, lecciones y Bloom' },
  { t: 'Auditor', d: 'Valida carga cognitiva y restricciones' },
  { t: 'Redactor', d: 'Redacta el contenido final' },
]

const StatusDot = ({ color, live }: { color: string; live?: boolean }) => (
  <span
    aria-hidden
    className={`intake-dot${live ? ' intake-dot--live' : ''}`}
    style={{
      display: 'inline-block',
      width: 7,
      height: 7,
      borderRadius: '50%',
      background: color,
      marginRight: 8,
      verticalAlign: 'middle',
      transform: 'translateY(-1px)',
    }}
  />
)

export default function NewCoursePage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const [draft, setDraft] = useState<Record<string, string>>({})
  const [freeText, setFreeText] = useState('')
  const [history, setHistory] = useState<IntakeTurn[]>([])
  const [assistant, setAssistant] = useState<IntakeResponse | null>(null)
  const [thinking, setThinking] = useState(false)
  const [error, setError] = useState('')

  const [activeKey, setActiveKey] = useState<keyof EnrichedInstructorInput>(
    INTAKE_FIELDS[0].key
  )
  const [globalReview, setGlobalReview] = useState(false)

  const [phase, setPhase] = useState<'idle' | 'running' | 'done'>('idle')
  const [step, setStep] = useState(0)
  const timer = useRef<number | null>(null)

  const score = computeScore(draft)
  const ready = score === 100

  const focusField = (key: keyof EnrichedInstructorInput) => {
    setActiveKey(key)
    setGlobalReview(false)
  }

  const consult = async () => {
    setError('')
    setThinking(true)
    setGlobalReview(true)
    const userContent = freeText.trim() || '(revisión completa del formulario)'
    try {
      const res = await intakeTurn({ draft, free_text: freeText.trim(), history })
      setAssistant(res)
      setHistory([
        ...history,
        { role: 'user', content: userContent },
        { role: 'assistant', content: res.assistant_message },
      ])
      setFreeText('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'El asistente no respondió')
    } finally {
      setThinking(false)
    }
  }

  const startProgress = () => {
    setStep(0)
    timer.current = window.setInterval(() => {
      setStep((s) => (s < STEPS.length - 1 ? s + 1 : s))
    }, 1100)
  }
  const finishProgress = () => {
    if (timer.current) window.clearInterval(timer.current)
    setStep(STEPS.length)
  }

  const generate = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setPhase('running')
    startProgress()
    try {
      let enriched = assistant?.enriched_input ?? null
      if (!enriched) {
        const r = await intakeTurn({ draft, free_text: '', history })
        setAssistant(r)
        enriched = r.enriched_input
      }
      if (!enriched) {
        throw new Error('El asistente no pudo completar la intención. Revisa los campos.')
      }
      // La intención viaja ESTRUCTURADA al backend: cada campo alimenta a su
      // agente (pilares→módulos, objetivo/entregable→diseño y cierre,
      // voz/tono/escenario/fuera-de-alcance→redacción). topic/audience/context
      // mapean a las columnas persistidas (listas y detalle).
      const res = await createCourse({
        topic: enriched.course_name,
        target_audience: enriched.audience_profile,
        additional_context: enriched.additional_context || undefined,
        course_name: enriched.course_name,
        creator_authority: enriched.creator_authority,
        operational_goal: enriched.operational_goal,
        final_deliverable: enriched.final_deliverable,
        audience_profile: enriched.audience_profile,
        content_pillars: enriched.content_pillars,
        application_context: enriched.application_context,
        out_of_scope: enriched.out_of_scope,
        tone: enriched.tone,
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

  const activeMeta = metaByKey(activeKey)
  const activeAdvice = activeMeta ? coachField(activeKey, draft[activeKey] || '') : null
  const activeColor =
    activeMeta && activeAdvice ? adviceColor(activeAdvice.state, activeMeta.required) : '#9aa39f'

  return (
    <>
      <Topbar title="Crear curso" crumb="Cursos / Nuevo" user={user} />
      <div className="content">
        <div className="intake-layout">
          {/* COLUMNA IZQUIERDA */}
          <div className="card reveal">
            <h2 className="section-title" style={{ fontSize: 20 }}>Define la intención del curso</h2>
            <p className="lead" style={{ marginBottom: 6 }}>
              No escribas un temario: escribe <b>qué va a saber hacer</b> el alumno y con qué huesos.
              El asistente te acompaña campo por campo.
            </p>

            <div style={{ margin: '14px 0 18px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--ink-faint)', marginBottom: 5 }}>
                <span>Campos obligatorios completos</span>
                <span style={{ fontWeight: 800, color: ready ? '#2e7d4f' : 'var(--ink)' }}>{score}%</span>
              </div>
              <div style={{ height: 8, background: 'rgba(0,0,0,0.07)', borderRadius: 6, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${score}%`, background: ready ? '#2e7d4f' : '#c9821f', borderRadius: 6, transition: 'width .45s ease' }} />
              </div>
            </div>

            {error && <div className="alert alert-error">{error}</div>}

            {INTAKE_FIELDS.map((f) => {
              const advice = coachField(f.key, draft[f.key] || '')
              const isActive = f.key === activeKey
              const ring = isActive ? { borderColor: '#c9821f', boxShadow: '0 0 0 2px rgba(201,130,31,0.18)' } : undefined
              return (
                <div className="form-group" key={f.key} style={{ marginBottom: 16 }}>
                  <label>
                    {f.label}{' '}
                    <span className="hint">· {f.required ? 'obligatorio' : 'opcional'}</span>
                  </label>
                  {f.area ? (
                    <textarea
                      value={draft[f.key] || ''}
                      onChange={(e) => { setDraft((d) => ({ ...d, [f.key]: e.target.value })); focusField(f.key) }}
                      onFocus={() => focusField(f.key)}
                      placeholder={f.example}
                      disabled={phase === 'running'}
                      style={ring}
                    />
                  ) : (
                    <input
                      value={draft[f.key] || ''}
                      onChange={(e) => { setDraft((d) => ({ ...d, [f.key]: e.target.value })); focusField(f.key) }}
                      onFocus={() => focusField(f.key)}
                      placeholder={f.example}
                      disabled={phase === 'running'}
                      style={ring}
                    />
                  )}
                  {f.help && (
                    <div style={{ fontSize: 12, color: 'var(--ink-faint)', marginTop: 4, lineHeight: 1.4 }}>
                      {f.help}
                    </div>
                  )}
                  {advice.state === 'good' && (
                    <div style={{ fontSize: 11.5, color: '#2e7d4f', marginTop: 3, fontWeight: 700 }}>✓</div>
                  )}
                </div>
              )
            })}

            <div className="form-group" style={{ marginTop: 6 }}>
              <label>Háblale al asistente en lenguaje natural <span className="hint">· opcional</span></label>
              <textarea
                value={freeText}
                onChange={(e) => setFreeText(e.target.value)}
                placeholder="Ej: quiero que sea muy práctico, paso a paso, para gente sin experiencia previa…"
                disabled={phase === 'running' || thinking}
              />
            </div>

            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={consult}
                disabled={thinking || phase === 'running'}
                style={{ borderColor: '#c9821f', color: '#c9821f', fontWeight: 700 }}
              >
                {thinking ? 'Revisando…' : 'Revisar todo con el asistente'}
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={generate}
                disabled={!ready || phase === 'running'}
              >
                {phase === 'running' ? <><span className="spinner" /> Generando curso…</> : 'Generar curso con IA'}
              </button>
            </div>
          </div>

          {/* COLUMNA DERECHA: asistente sticky */}
          <div className="intake-aside">
            <div className="card reveal-2 intake-sticky" style={{ padding: '22px 24px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'baseline',
                  justifyContent: 'space-between',
                  paddingBottom: 12,
                  marginBottom: 18,
                  borderBottom: '1px solid rgba(0,0,0,0.07)',
                }}
              >
                <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-faint)' }}>
                  Asistente
                </span>
                <span style={{ fontSize: 10, color: 'rgba(0,0,0,0.32)', fontFamily: 'ui-monospace, monospace', letterSpacing: '0.04em' }}>
                  {assistant ? assistant.mode : 'local'}
                </span>
              </div>

              {ready && (
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: 18 }}>
                  <StatusDot color="#2e7d4f" />
                  <span style={{ fontSize: 13.5, fontWeight: 700, color: '#2e7d4f' }}>
                    Intención lista
                  </span>
                  <span style={{ fontSize: 12.5, color: 'var(--ink-faint)', marginLeft: 8 }}>
                    ya puedes generar el curso
                  </span>
                </div>
              )}

              <div key={`${activeKey}-${globalReview ? 'g' : 'c'}`} style={{ animation: 'reveal .35s ease' }}>
                {globalReview && assistant ? (
                  <>
                    <p style={{ margin: '0 0 16px', lineHeight: 1.7, fontSize: 14.5, color: 'var(--ink)' }}>
                      {assistant.assistant_message}
                    </p>
                    {assistant.clarifications.length > 0 && (
                      <>
                        <div style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-faint)', marginBottom: 10 }}>
                          Por pulir
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                          {assistant.clarifications.slice(0, 5).map((c, i) => (
                            <div key={i} style={{ lineHeight: 1.5 }}>
                              <div style={{ fontSize: 13.5, color: 'var(--ink)' }}>{c.question}</div>
                              {c.example && (
                                <div style={{ fontSize: 12, color: 'var(--ink-faint)', fontStyle: 'italic', marginTop: 2 }}>
                                  ej. {c.example}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </>
                    )}
                    <div style={{ marginTop: 16, fontSize: 11.5, color: 'rgba(0,0,0,0.38)' }}>
                      Toca cualquier campo para volver al acompañamiento paso a paso.
                    </div>
                  </>
                ) : activeMeta && activeAdvice ? (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                      <StatusDot color={activeColor} live={activeAdvice.state !== 'good'} />
                      <span style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-faint)' }}>
                        {activeMeta.short}
                      </span>
                    </div>
                    <p style={{ margin: '0 0 4px', lineHeight: 1.7, fontSize: 14.5, color: 'var(--ink)' }}>
                      {activeAdvice.message}
                    </p>
                    {activeAdvice.state !== 'good' && (
                      <div style={{ marginTop: 12, fontSize: 12, color: 'var(--ink-faint)', lineHeight: 1.5 }}>
                        <span style={{ fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', fontSize: 10.5, marginRight: 6 }}>Ejemplo</span>
                        {activeMeta.example}
                      </div>
                    )}
                  </>
                ) : (
                  <p style={{ margin: 0, lineHeight: 1.7, fontSize: 14, color: 'var(--ink-faint)' }}>
                    Completa los campos de la izquierda; aquí te acompaño uno por uno.
                  </p>
                )}
              </div>
            </div>

            {phase === 'running' && (
              <div className="card reveal-2" style={{ padding: '22px 24px' }}>
                <h2 className="section-title" style={{ fontSize: 16 }}>Construyendo tu curso</h2>
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
      </div>
    </>
  )
}