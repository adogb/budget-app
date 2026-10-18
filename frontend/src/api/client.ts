// fetch() only rejects on network failure, so an HTTP error like 500 has to
// be turned into an exception here. TanStack Query then shows it as an error.
async function request<T>(
  method: 'GET' | 'POST' | 'PATCH' | 'PUT',
  path: string,
  body?: unknown,
): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(await errorMessage(response))
  }
  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

// The API explains its errors in `detail`, e.g. "Euro savings is in EUR currency…".
async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') {
      return body.detail
    }
  } catch {
    // Not JSON, e.g. a proxy error page.
  }
  return `${response.status} ${response.statusText}`
}

export function getJson<T>(path: string): Promise<T> {
  return request<T>('GET', path)
}

export function postJson<T>(path: string, body?: unknown): Promise<T> {
  return request<T>('POST', path, body)
}

export function patchJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>('PATCH', path, body)
}

export function putJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>('PUT', path, body)
}
