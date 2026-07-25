export interface Tenant {
  id: string
  name: string
  slug: string
  is_active: boolean
  created_at: string
}

export interface TenantDetail extends Tenant {
  accreditation_rules: AccreditationRules
}

export interface UserWithTenant {
  id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  created_at: string
  tenant: Tenant
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface RegisterData {
  tenant_name: string
  tenant_slug: string
  email: string
  password: string
  full_name: string
}

export interface LoginData {
  username: string
  password: string
}

export type BloomLevel =
  | 'remember' | 'understand' | 'apply'
  | 'analyze' | 'evaluate' | 'create'

export interface AccreditationRules {
  min_total_hours: number
  max_total_hours: number
  min_module_hours: number
  max_module_hours: number
  required_bloom_levels: BloomLevel[]
  min_lessons_per_module: number
  max_lessons_per_module: number
  custom_restrictions: string | null
}

export interface CourseSummary {
  id: string
  topic: string
  target_audience: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface MatrixLesson {
  lesson_id: string
  title: string
  bloom_level: BloomLevel
  estimated_hours: number
  learning_objective: string
  key_topics: string[]
}

export interface MatrixModule {
  module_id: string
  title: string
  description: string
  estimated_hours: number
  lessons: MatrixLesson[]
}

export interface CourseMatrix {
  course_id: string
  course_title: string
  topic: string
  total_estimated_hours: number
  modules: MatrixModule[]
  bloom_distribution: Record<string, number>
}

export interface LessonContent {
  lesson_id: string
  title: string
  full_content: string
  activities: string[]
  assessment_criteria: string[]
  estimated_hours: number
}

export interface CourseContent {
  course_id: string
  course_title: string
  lessons_content: LessonContent[]
  generated_at: string
}

export interface CourseResponse {
  id: string
  tenant_id: string
  created_by: string
  topic: string
  target_audience: string | null
  additional_context: string | null
  status: string
  course_matrix: CourseMatrix | null
  quality_report: Record<string, unknown> | null
  course_content: CourseContent | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface CreateCourseData {
  topic: string
  target_audience?: string
  additional_context?: string
}