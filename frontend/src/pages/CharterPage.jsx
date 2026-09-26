import { useEffect, useState } from 'react'
import { createBooking, getAvailability, getShips } from '../api.js'
import { formatDate, formatDuration, formatTime, todayInCentral } from '../time.js'

const STATUS_LABELS = {
  available: 'Available',
  booked: 'Booked',
  refueling: 'Refueling',
  past: 'Unavailable (Past)',
}

export default function CharterPage() {
  const [ships, setShips] = useState([])
  const [shipId, setShipId] = useState('')
  const [date, setDate] = useState(todayInCentral())
  const [slots, setSlots] = useState([])

  // Keep track of the first and last selected time slots
  const [selection, setSelection] = useState(null)

  const [pilotName, setPilotName] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState(null)

  useEffect(() => {
    getShips()
      .then((data) => {
        setShips(data)
        if (data.length) setShipId(String(data[0].id))
      })
      .catch((e) => setMessage({ type: 'error', text: e.message }))
  }, [])

  // Used to refresh availability after trying to make a booking
  const [reloadKey, setReloadKey] = useState(0)
  const requestKey = `${shipId}|${date}|${reloadKey}`
  const [loadedKey, setLoadedKey] = useState(null)
  const loading = loadedKey !== requestKey

  useEffect(() => {
    if (!shipId) return

    // Don't update the page if the user switches ships or dates while this is loading
    let cancelled = false

    getAvailability(shipId, date)
      .then((data) => !cancelled && setSlots(data.slots))
      .catch((e) => {
        if (cancelled) return

        setSlots([])
        setMessage({ type: 'error', text: e.message })
      })
      .finally(() => !cancelled && setLoadedKey(requestKey))

    return () => {
      cancelled = true
    }
  }, [shipId, date, requestKey])

  function changeShip(value) {
    setShipId(value)
    setSelection(null)
  }

  function changeDate(value) {
    if (!value) return

    setDate(value)
    setSelection(null)
  }

  function handleSlotClick(index) {
    if (slots[index].status !== 'available') return

    setMessage(null)

    // Start a new selection
    if (!selection || selection.start !== selection.end) {
      setSelection({ start: index, end: index })
      return
    }

    // Clicking the same slot again clears the selection
    if (index === selection.start) {
      setSelection(null)
      return
    }

    // Make sure all slots between the start and end time are available
    const start = Math.min(index, selection.start)
    const end = Math.max(index, selection.start)

    const allFree = slots
      .slice(start, end + 1)
      .every((s) => s.status === 'available')

    setSelection(
      allFree
        ? { start, end }
        : { start: index, end: index }
    )
  }

  async function handleBook(e) {
    e.preventDefault()

    if (!selection) return

    setSubmitting(true)
    setMessage(null)

    const startTime = slots[selection.start].start
    const endTime = slots[selection.end].end

    try {
      await createBooking({
        shipId: Number(shipId),
        pilotName,
        startTime,
        endTime,
      })

      const ship = ships.find((s) => String(s.id) === shipId)

      setMessage({
        type: 'success',
        text: `Booked ${ship?.name} for ${pilotName}, ${formatTime(startTime)}–${formatTime(endTime)} CT.`,
      })

      setPilotName('')
    } catch (e) {
      setMessage({
        type: 'error',
        text: e.message,
      })
    } finally {
      // Refresh the slots in case availability changed
      setSelection(null)
      setSubmitting(false)
      setReloadKey((k) => k + 1)
    }
  }

  const isSelected = (i) =>
    selection && i >= selection.start && i <= selection.end

  const selStart = selection && slots[selection.start]?.start
  const selEnd = selection && slots[selection.end]?.end

  return (
    <section>
      <h1>Charter a Ship</h1>

      <div className="controls">
        <label>
          Ship
          <select
            value={shipId}
            onChange={(e) => changeShip(e.target.value)}
          >
            {ships.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Date
          <input
            type="date"
            value={date}
            min={todayInCentral()}
            onChange={(e) => changeDate(e.target.value)}
          />
        </label>
      </div>

      <p className="hint">
        All times are Central Time. Operating hours are 6:00 AM to 10:00 PM.
        Click a start slot, then an end slot.
      </p>

      <div className="legend">
        {Object.entries(STATUS_LABELS).map(([status, label]) => (
          <span
            key={status}
            className={`legend-item slot-${status}`}
          >
            {label}
          </span>
        ))}

        <span className="legend-item slot-selected">
          Selected
        </span>
      </div>

      {loading && !slots.length ? (
        <p>Loading…</p>
      ) : (
        <div className={`slot-grid ${loading ? 'is-loading' : ''}`}>
          {slots.map((slot, i) => (
            <button
              key={slot.start}
              type="button"
              className={`slot slot-${isSelected(i) ? 'selected' : slot.status}`}
              disabled={slot.status !== 'available'}
              onClick={() => handleSlotClick(i)}
              title={STATUS_LABELS[slot.status]}
            >
              {formatTime(slot.start)}
            </button>
          ))}
        </div>
      )}

      <form className="booking-form" onSubmit={handleBook}>
        <div className="selection-summary">
          {selection ? (
            <>
              <strong>{formatDate(selStart)}</strong>,{' '}
              {formatTime(selStart)} – {formatTime(selEnd)} CT
              <span className="muted">
                {' '}({formatDuration(selStart, selEnd)})
              </span>
            </>
          ) : (
            <span className="muted">No time selected</span>
          )}
        </div>

        <label>
          Pilot name
          <input
            value={pilotName}
            onChange={(e) => setPilotName(e.target.value)}
            placeholder="e.g. John Doe"
            maxLength={100}
            required
          />
        </label>

        <button
          type="submit"
          className="primary"
          disabled={!selection || !pilotName.trim() || submitting}
        >
          {submitting ? 'Booking…' : 'Book charter'}
        </button>
      </form>

      {message && (
        <p className={`message message-${message.type}`}>
          {message.text}
        </p>
      )}
    </section>
  )
}