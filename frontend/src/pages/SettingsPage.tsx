import { useEffect, useState, FormEvent } from 'react'
import { useAuth } from '../context/AuthContext'
import { Topbar } from '../components/Layout'
import { getMyTenant, updateRules } from '../api/endpoints'
import { AccreditationRules, BloomLevel } from '../types'

const BLOOMS: BloomLevel[] = ['remember', 'understand', 'apply', 'analyze', 'evaluate', 'create']

const emptyRules: AccreditationRules = {
  min_total_hours: 20, max_total_hours: 40,
  min_module_hours: 4, max_module_hours: 10,
  required_bloom_levels: ['remember', 'apply'],
  min_lessons_per_module: 2, max_lessons_per_module: 5,
  custom_restrictions: null,
}

export default function SettingsPage() {
  const { user } = useAuth()
  const [rules, setRules] = useState<AccreditationRules>(emptyRules)
  const [custom, setCustom] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const isAdmin = user?.role === 'admin'

  useEffect(() => {
    getMyTenant()
      .then(t => { setRules(t.accreditation_rules); setCustom(t.accreditation_rules.custom_restrictions ?? '') })
      .catch(() => setMsg({ type: 'error', text: 'No se pudieron cargar las reglas.' }))
      .finally(() => setLoading(false))
  }, [])

  const toggleBloom = (b: BloomLevel) => {
    setRules(r => ({
      ...r,
      required_bloom_levels: r.required_bloom_levels.includes(b)
        ? r.required_bloom_levels.filter(x => x !== b)
        : [...r.required_bloom_levels, b],
    }))
  }

  const setNum = (k: keyof AccreditationRules, v: string) =>
    setRules(r => ({ ...r, [k]: v === '' ? 0 : Number(v) }))

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setMsg(null); setSaving(true)
    try {
      const payload = { ...rules, custom_restrictions: custom.trim() || null }
      const t = await updateRules(payload)
      setRules(t.accreditation_rules)
      setCustom(t.accreditation_rules.custom_restrictions ?? '')
      setMsg({ type: 'success', text: 'Reglas actualizadas. Se aplicarán a los próximos cursos.' })
    } catch (err) {
      setMsg({ type: 'error', text: err instanceof Error ? err.message : 'No se pudieron guardar las reglas.' })
    } finally {
      setSaving(false)
    }
  }

  if (!user) return null

  return (
    <>
      <Topbar title="Reglas del colegio" crumb="Configuración" user={user} />
      <div className="content">
        {!isAdmin && (
          <div className="alert alert-info">Solo los administradores del colegio pueden editar las reglas de acreditación.</div>
        )}

        {loading ? (
          <div className="card" style={{ textAlign: 'center', color: 'var(--ink-faint)' }}>Cargando reglas…</div>
        ) : (
          <form onSubmit={handleSubmit} className="card reveal">
            <h2 className="section-title" style={{ fontSize: 20 }}>Reglas de acreditación</h2>
            <p className="lead" style={{ marginBottom: 22 }}>
              Estos límites los respeta el motor al diseñar cada curso de <b style={{ color: 'var(--ink)' }}>{user.tenant.name}</b>.
            </p>

            {msg && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

            <div className="form-row">
              <div className="form-group">
                <label>Horas totales · mínimo</label>
                <input type="number" min={1} value={rules.min_total_hours} onChange={e => setNum('min_total_hours', e.target.value)} disabled={!isAdmin} />
              </div>
              <div className="form-group">
                <label>Horas totales · máximo</label>
                <input type="number" min={1} value={rules.max_total_hours} onChange={e => setNum('max_total_hours', e.target.value)} disabled={!isAdmin} />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Horas por módulo · mínimo</label>
                <input type="number" min={1} value={rules.min_module_hours} onChange={e => setNum('min_module_hours', e.target.value)} disabled={!isAdmin} />
              </div>
              <div className="form-group">
                <label>Horas por módulo · máximo</label>
                <input type="number" min={1} value={rules.max_module_hours} onChange={e => setNum('max_module_hours', e.target.value)} disabled={!isAdmin} />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Lecciones por módulo · mínimo</label>
                <input type="number" min={1} value={rules.min_lessons_per_module} onChange={e => setNum('min_lessons_per_module', e.target.value)} disabled={!isAdmin} />
              </div>
              <div className="form-group">
                <label>Lecciones por módulo · máximo</label>
                <input type="number" min={1} value={rules.max_lessons_per_module} onChange={e => setNum('max_lessons_per_module', e.target.value)} disabled={!isAdmin} />
              </div>
            </div>

            <div className="form-group">
              <label>Niveles de Bloom obligatorios <span className="hint">· elige al menos uno</span></label>
              <div className="bloom-pick">
                {BLOOMS.map(b => (
                  <label key={b}>
                    <input type="checkbox" checked={rules.required_bloom_levels.includes(b)} onChange={() => toggleBloom(b)} disabled={!isAdmin} />
                    <span className={`badge bloom bloom-${b}`}>{b}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="form-group">
              <label>Restricción adicional <span className="hint">· opcional, en lenguaje natural</span></label>
              <textarea value={custom} onChange={e => setCustom(e.target.value)} placeholder="Incluir un estudio de caso obligatorio por módulo, alineado a la norma vigente…" disabled={!isAdmin} />
            </div>

            {isAdmin && (
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? <><span className="spinner" /> Guardando…</> : 'Guardar reglas'}
              </button>
            )}
          </form>
        )}
      </div>
    </>
  )
}