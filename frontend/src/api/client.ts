// fetch() only rejects on network failure, so an HTTP error like 500 has to
// be turned into an exception here. TanStack Query then shows it as an error.
export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) {
    throw new Error(`GET ${path} failed: ${response.status} ${response.statusText}`)
  }
  return response.json() as Promise<T>
}
