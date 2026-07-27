const API_BASE = '/api/v1'

/**
 * Cliente HTTP mínimo del frontend.
 *
 * Blindaje de respuestas sin cuerpo (204/205): el borrado de curso devuelve
 * 204 sin payload; parsear el cuerpo como JSON directamente sobre un cuerpo
 * vacío lanza SyntaxError y rompería la UI aunque el backend hubiera borrado
 * bien. Por eso leemos el cuerpo como texto y solo parseamos JSON si viene algo.
 * El manejo de error también tolera detalles que no sean JSON válido.
 */
export async function apiRequest<T>(
  method: string,
  path: string,
  body?: unknown,
  options?: { isForm?: boolean }
): Promise<T> {
  const token = localStorage.getItem('access_token')
  const headers: Record<string, string> = {}
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  let fetchBody: BodyInit | undefined
  if (body !== undefined) {
    if (options?.isForm) {
      headers['Content-Type'] = 'application/x-www-form-urlencoded'
      fetchBody = new URLSearchParams(body as Record<string, string>)
    } else {
      headers['Content-Type'] = 'application/json'
      fetchBody = JSON.stringify(body)
    }
  }

  const resp = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: fetchBody,
  })

  if (!resp.ok) {
    const errText = await resp.text()
    let detail = resp.statusText
    if (errText) {
      try {
        const parsed = JSON.parse(errText)
        detail = parsed?.detail || detail
      } catch {
        detail = errText
      }
    }
    throw new Error(detail || `Error ${resp.status}`)
  }

  const text = await resp.text()
  if (!text) return undefined as unknown as T
  return JSON.parse(text) as T
}
