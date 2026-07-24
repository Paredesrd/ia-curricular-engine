import { apiRequest } from './client'
import {
  CourseResponse, CourseSummary, CreateCourseData,
  TenantDetail, AccreditationRules,
} from '../types'

export const listCourses = () =>
  apiRequest<CourseSummary[]>('GET', '/courses')

export const createCourse = (data: CreateCourseData) =>
  apiRequest<CourseResponse>('POST', '/courses', data)

export const getCourse = (id: string) =>
  apiRequest<CourseResponse>('GET', `/courses/${id}`)

export const getMyTenant = () =>
  apiRequest<TenantDetail>('GET', '/tenants/me')

export const updateRules = (rules: AccreditationRules) =>
  apiRequest<TenantDetail>('PUT', '/tenants/me/rules', rules)