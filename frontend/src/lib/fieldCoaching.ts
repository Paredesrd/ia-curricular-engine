// frontend/src/lib/fieldCoaching.ts
// Definición de los campos del intake + acompañamiento por campo (coaching).
// Función única: ser la fuente de verdad de (a) qué campos se piden y cómo se
// presentan, y (b) qué decirle al instructor sobre cada campo mientras escribe.
// El coaching es determinista (sin red). Cuando entre el LLM, esta misma burbuja
// la llenará el modelo por campo; la UI (NewCoursePage) no cambia.

import type { EnrichedInstructorInput } from '../types'

export type IntakeFieldMeta = {
  key: keyof EnrichedInstructorInput
  label: string // título conversacional del campo (encima del input)
  short: string // nombre corto (para el panel del asistente)
  help: string // explicación pequeña en gris (debajo del input)
  example: string // placeholder sobreescribible
  required: boolean
  area?: boolean
}

// Orden = orden visual del formulario.
export const INTAKE_FIELDS: IntakeFieldMeta[] = [
  {
    key: 'course_name',
    label: 'Escribe el nombre del curso',
    short: 'Nombre del curso',
    help: '',
    example: 'Elaboración de un Proyecto Social Comunitario',
    required: true,
  },
  {
    key: 'creator_authority',
    label: '¿Desde qué rol y experiencia hablas?',
    short: 'Voz / autoridad',
    help: 'Esto define la voz del audio y del video.',
    example: 'Trabajador social con 15 años en desarrollo comunitario',
    required: true,
  },
  {
    key: 'operational_goal',
    label: '¿Qué sabrá hacer el alumno al terminar?',
    short: 'Objetivo final',
    help: 'Piensa en el resultado observable, no en el temario.',
    example: 'Que el alumno arme y presente un proyecto social financiable',
    required: true,
    area: true,
  },
  {
    key: 'final_deliverable',
    label: '¿Qué entrega el alumno con sus manos al final?',
    short: 'Entregable final',
    help: 'Un objeto tangible: un documento, un plan, un prototipo…',
    example: 'Un documento con diagnóstico, plan de acción y presupuesto',
    required: true,
    area: true,
  },
  {
    key: 'audience_profile',
    label: '¿A quién va dirigido y cuánto sabe ya?',
    short: 'Audiencia y nivel',
    help: 'Incluye el nivel de entrada: novato, intermedio o experto.',
    example: 'Líderes comunitarios sin formación técnica previa (novatos)',
    required: true,
  },
  {
    key: 'content_pillars',
    label: 'Lista los 3 a 5 pasos o conceptos innegociables',
    short: 'Pilares del curso',
    help: 'Cada pilar se vuelve un módulo; el motor pone el músculo.',
    example: '1) Diagnóstico participativo  2) Árbol de problemas  3) Plan de acción  4) Presupuesto básico',
    required: true,
    area: true,
  },
  {
    key: 'application_context',
    label: '¿Dónde o en qué caso real se aplicará?',
    short: 'Escenario real',
    help: 'Un sector, comunidad o caso concreto sitúa los ejemplos.',
    example: 'Comunidades rurales con recursos limitados',
    required: true,
  },
  {
    key: 'out_of_scope',
    label: '¿Qué temas NO vas a tocar?',
    short: 'Fuera de alcance',
    help: 'Acotar aquí evita que el curso se dispare en duración.',
    example: 'No hablar de financiamiento gubernamental ni historia agrícola',
    required: true,
    area: true,
  },
  {
    key: 'tone',
    label: 'Elige el tono del curso',
    short: 'Tono',
    help: 'Si lo dejas vacío, usaremos un tono cercano y claro.',
    example: 'Cercano y motivador, como un mentor de campo',
    required: false,
  },
  {
    key: 'additional_context',
    label: 'Añade algún matiz extra (opcional)',
    short: 'Notas extra',
    help: 'Los requisitos obligatorios van en sus campos, no aquí.',
    example: 'Incluir al menos un caso real latinoamericano por módulo',
    required: false,
    area: true,
  },
]

const REQUIRED_FIELDS = INTAKE_FIELDS.filter((f) => f.required)

export const isFilled = (v: unknown): boolean =>
  v !== null && v !== undefined && String(v).trim() !== ''

// Porcentaje de campos OBLIGATORIOS completos (barra de progreso).
export const computeScore = (draft: Record<string, string>): number => {
  const done = REQUIRED_FIELDS.filter((f) => isFilled(draft[f.key])).length
  return Math.round((done / REQUIRED_FIELDS.length) * 100)
}

export const metaByKey = (key: keyof EnrichedInstructorInput): IntakeFieldMeta | undefined =>
  INTAKE_FIELDS.find((f) => f.key === key)

// --- Acompañamiento por campo (coaching determinista) ---
export type AdviceState = 'empty' | 'weak' | 'good'
export type FieldAdvice = {
  state: AdviceState
  message: string
}

const countPillars = (v: string): number => {
  const nums = v.match(/(?:^|[\s;])\d[\).:]/g)
  if (nums && nums.length >= 2) return nums.length
  return v
    .split(/[\n;]/)
    .map((s) => s.trim())
    .filter(Boolean).length
}

const RESULT_VERB =
  /que (el|la|los|las)|ser capaz|lograr|logre|diseñar|construir|elaborar|resolver|aplicar|implementar|crear|analizar|evaluar|preparar|armar|presentar|desarrollar|gestionar|planificar/i
const CREDENTIAL = /\d|años|experiencia|experto|especialista|especializado|docente|profesional|consultor/i
const LEVEL = /novat|principiant|sin experiencia|básic|intermed|avanz|experto|con experiencia|profesional|estudiant/i
const ARTIFACT =
  /documento|plan|proyecto|prototipo|informe|guía|guia|manual|propuesta|presupuesto|diagnóstico|diagnostico|modelo|presentación|presentacion|matriz|hoja de ruta|cronograma|dossier/i
const VAGUE = /general|cualquier|todo|varios|diversos|cualquiera/i

export function coachField(
  key: keyof EnrichedInstructorInput,
  value: string
): FieldAdvice {
  const v = (value || '').trim()
  if (!isFilled(v)) {
    const emptyMsg: Record<string, string> = {
      course_name: 'Escribe el nombre tal como aparecería en el catálogo.',
      creator_authority: 'Dime desde qué rol hablas: eso da la voz del curso.',
      operational_goal: 'El destino del curso: ¿qué sabrá hacer el alumno al final?',
      final_deliverable: '¿Qué objeto entrega el alumno con sus manos al terminar?',
      audience_profile: 'Define a quién va dirigido y cuánto sabe ya.',
      content_pillars: 'Enumera los 3 a 5 pasos que sí o sí debe enseñar.',
      application_context: 'Sitúa el caso real donde se aplicará esto.',
      out_of_scope: 'Anota lo que no vas a tocar para acotar la duración.',
      tone: 'Si lo dejas vacío, usaremos un tono cercano y claro.',
      additional_context: 'Opcional. Los requisitos obligatorios van en sus campos.',
    }
    return { state: 'empty', message: emptyMsg[key] || 'Completa este campo.' }
  }

  switch (key) {
    case 'course_name':
      return v.length < 12 || v.split(/\s+/).length < 2
        ? { state: 'weak', message: 'Un poco corto: añade qué se aprende o para quién.' }
        : { state: 'good', message: 'Nombre claro ✓' }
    case 'creator_authority':
      return CREDENTIAL.test(v)
        ? { state: 'good', message: 'Autoridad definida ✓' }
        : { state: 'weak', message: 'Añade una credencial concreta (años, especialidad) para que la voz suene con autoridad.' }
    case 'operational_goal':
      return RESULT_VERB.test(v)
        ? { state: 'good', message: 'Objetivo orientado a resultado ✓' }
        : { state: 'weak', message: 'Suena a tema, no a resultado. Empieza por lo observable: “Que el alumno logre…”.' }
    case 'final_deliverable':
      return ARTIFACT.test(v)
        ? { state: 'good', message: 'Entregable tangible ✓' }
        : { state: 'weak', message: 'Concreta el artefacto: un documento, un plan, un prototipo… algo que se entrega.' }
    case 'audience_profile':
      return LEVEL.test(v)
        ? { state: 'good', message: 'Audiencia y nivel definidos ✓' }
        : { state: 'weak', message: 'Añade el nivel de entrada (novato / intermedio / experto): define cuánto explico desde cero.' }
    case 'content_pillars': {
      const n = countPillars(v)
      if (n < 3) return { state: 'weak', message: 'Pon al menos 3 pilares para que el índice tenga cuerpo.' }
      if (n > 5) return { state: 'weak', message: 'Más de 5 dispersa: quédate con los innegociables.' }
      return { state: 'good', message: `Pilares bien acotados ✓ (${n})` }
    }
    case 'application_context':
      return v.length < 8 || VAGUE.test(v)
        ? { state: 'weak', message: 'Sitúa el escenario: un tipo de comunidad, sector o caso concreto.' }
        : { state: 'good', message: 'Escenario situado ✓' }
    case 'out_of_scope':
      return { state: 'good', message: 'Límites definidos ✓ (acotan el curso)' }
    case 'tone':
      return { state: 'good', message: 'Tono definido ✓' }
    case 'additional_context':
      return { state: 'good', message: 'Notas añadidas ✓' }
    default:
      return { state: 'good', message: '✓' }
  }
}

// Color del coaching según estado (y si el campo es obligatorio).
export const adviceColor = (state: AdviceState, required: boolean): string => {
  if (state === 'good') return '#2e7d4f'
  if (!required) return '#6b7280' // opcional vacío = gris, no alarma
  return state === 'weak' ? '#b4541f' : '#c9821f'
}