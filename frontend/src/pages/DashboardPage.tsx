import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Topbar } from '../components/Layout'
import { listCourses } from '../api/endpoints'

export default function DashboardPage() {
  const { user } = useAuth()
  const [count, setCount] = useState<number | null>(null)

  useEffect(() => {
    listCourses().then(list => setCount(list.length)).catch(() => setCount(0))
  }, [])

  if (!user) return null

  return (
    <>
      <Topbar title={`Bienvenido, ${user.full_name.split(' ')[0]}`} crumb="Inicio" user={user} />
      <div className="content">
        <div className="stat-grid">
          <div className="stat reveal">
            <div className="k">Colegio</div>
            <div className="v" style={{ fontSize: 22 }}>{user.tenant.name}</div>
            <div className="s">/{user.tenant.slug}</div>
          </div>
          <div className="stat reveal-2">
            <div className="k">Tu rol</div>
            <div className="v" style={{ fontSize: 22, textTransform: 'capitalize' }}>{user.role}</div>
            <div className="s">{user.role === 'admin' ? 'Puedes editar las reglas' : 'Puedes crear cursos'}</div>
          </div>
          <div className="stat reveal-3">
            <div className="k">Cursos generados</div>
            <div className="v">{count === null ? '…' : count}</div>
            <div className="s">en este colegio</div>
          </div>
        </div>

        <p className="lead reveal" style={{ marginBottom: 22 }}>
          El motor convierte un tema técnico en un curso completo y acreditado: módulos, lecciones con nivel cognitivo,
          horas, actividades y criterios de evaluación, respetando las reglas de tu colegio.
        </p>

        <div className="grid-cards">
          <Link to="/courses/new" className="tile reveal">
            <span className="arrow">↗</span>
            <h3>Crear un curso</h3>
            <p>Escribe el tema y el motor diseña y redacta el curso completo en segundos.</p>
          </Link>
          <Link to="/courses" className="tile reveal-2">
            <span className="arrow">↗</span>
            <h3>Mis cursos</h3>
            <p>Revisa los cursos ya generados, módulo por módulo.</p>
          </Link>
          {user.role === 'admin' && (
            <Link to="/settings" className="tile reveal-3">
              <span className="arrow">↗</span>
              <h3>Reglas del colegio</h3>
              <p>Ajusta horas, niveles de Bloom obligatorios y restricciones de acreditación.</p>
            </Link>
          )}
        </div>
      </div>
    </>
  )
}