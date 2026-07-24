const API_BASE = '/api/v1'

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
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || `Error ${resp.status}`)
  }

  return resp.json()
}