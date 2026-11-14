const API_ROOT = '/api'

async function readResponse(response) {
  const payload = await response.json().catch(() => null)
  if (response.ok) return payload
  throw new Error(typeof payload?.detail === 'string' ? payload.detail : 'La solicitud no pudo completarse.')
}

export const api = {
  get: async path => readResponse(await fetch(`${API_ROOT}${path}`)),
  post: async (path, body) => readResponse(await fetch(`${API_ROOT}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })),
}
