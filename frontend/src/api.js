const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    const error = new Error(errorMessage(body) ?? `Request failed (${res.status})`)
    error.status = res.status
    throw error
  }
  return body
}

// FastAPI sends `detail` as a string for our own errors, or as a list for validation errors.
function errorMessage(body) {
  const detail = body?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join('; ')
  return null
}

export const getShips = () => request('/ships')

export const getAvailability = (shipId, date) =>
  request(`/ships/${shipId}/availability?date=${date}`)

export const getBookings = ({ shipId, fromDate, toDate } = {}) => {
  const params = new URLSearchParams()
  if (shipId) params.set('shipId', shipId)
  if (fromDate) params.set('fromDate', fromDate)
  if (toDate) params.set('toDate', toDate)
  return request(`/bookings?${params}`)
}

export const createBooking = (booking) =>
  request('/bookings', { method: 'POST', body: JSON.stringify(booking) })
