import { apiRequest } from './client'
import {
  CourseResponse,
  CourseSummary,
  CreateCourseData,
  TenantDetail,
  AccreditationRules,
  IntakeRequest,
  IntakeResponse,
} from '../types'

export const listCourses = () =>
  apiRequest<CourseSummary[]>('GET', '/courses')

export const createCourse = (data: CreateCourseData) =>
  apiRequest<CourseResponse>('POST', '/courses', data)

export const getCourse = (id: string) =>
  apiRequest<CourseResponse>('GET', `/courses/${id}`)

// Elimina un curso. El backend responde 204 sin cuerpo; el cliente blindado
// devuelve undefined. El aislamiento multi-tenant lo garantiza el router
// (curso ajeno -> 404; sin token -> 401).
export const deleteCourse = (id: string) =>
  apiRequest<void>('DELETE', `/courses/${id}`)

export const getMyTenant = () =>
  apiRequest<TenantDetail>('GET', '/tenants/me')

export const updateRules = (rules: AccreditationRules) =>
  apiRequest<TenantDetail>('PUT', '/tenants/me/rules', rules)

// Un turno del intake conversacional (agente Elicitor).
export const intakeTurn = (data: IntakeRequest) =>
  apiRequest<IntakeResponse>('POST', '/intake', data)