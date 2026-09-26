import { useEffect, useMemo, useState } from 'react'
import { getBookings, getShips } from '../api.js'
import { addDays, formatDate, formatDuration, formatTime, todayInCentral } from '../time.js'

export default function ManagerPage() {
  const [ships, setShips] = useState([])
  const [bookings, setBookings] = useState([])
  const [fromDate, setFromDate] = useState(todayInCentral())
  const [toDate, setToDate] = useState(addDays(todayInCentral(), 6))
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getShips().then(setShips).catch((e) => setError(e.message))
  }, [])

  function changeRange(from, to) {
    if (!from || !to) return
    setFromDate(from)
    setToDate(to)
    setLoading(true)
    setError(null)
  }

  useEffect(() => {
    // Don't update the page if the date range changes while this is loading
    let cancelled = false
    getBookings({ fromDate, toDate })
      .then((data) => !cancelled && setBookings(data))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [fromDate, toDate])

  // Group the bookings by ship so each ship can show its own list
  const bookingsByShip = useMemo(() => {
    const groups = new Map(ships.map((s) => [s.id, []]))
    for (const b of bookings) groups.get(b.shipId)?.push(b)
    return groups
  }, [ships, bookings])

  return (
    <section>
      <h1>Fleet Manager</h1>

      <div className="controls">
        <label>
          From
          <input type="date" value={fromDate} max={toDate} onChange={(e) => changeRange(e.target.value, toDate)} />
        </label>
        <label>
          To
          <input type="date" value={toDate} min={fromDate} onChange={(e) => changeRange(fromDate, e.target.value)} />
        </label>
        <span className="muted summary-count">
          {loading ? 'Loading…' : `${bookings.length} booking${bookings.length === 1 ? '' : 's'}`}
        </span>
      </div>

      {error && <p className="message message-error">{error}</p>}

      <div className="fleet">
        {ships.map((ship) => {
          const shipBookings = bookingsByShip.get(ship.id) ?? []
          return (
            <details key={ship.id} className="ship-card" >
              <summary>
                <span className="ship-name">{ship.name}</span>
                <span className="badge">{shipBookings.length}</span>
              </summary>
              {shipBookings.length === 0 ? (
                <p className="muted empty">No bookings in this range.</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Time (CT)</th>
                      <th>Duration</th>
                      <th>Pilot</th>
                    </tr>
                  </thead>
                  <tbody>
                    {shipBookings.map((b) => (
                      <tr key={b.id}>
                        <td>{formatDate(b.startTime)}</td>
                        <td>{formatTime(b.startTime)} – {formatTime(b.endTime)}</td>
                        <td>{formatDuration(b.startTime, b.endTime)}</td>
                        <td>{b.pilotName}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </details>
          )
        })}
      </div>
    </section>
  )
}