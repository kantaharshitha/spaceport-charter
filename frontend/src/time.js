// The API speaks in UTC instants; everything shown to users is in spaceport (Central) time.
const TIME_ZONE = 'America/Chicago'

const timeFormat = new Intl.DateTimeFormat('en-US', {
  timeZone: TIME_ZONE,
  hour: 'numeric',
  minute: '2-digit',
})

const dateFormat = new Intl.DateTimeFormat('en-US', {
  timeZone: TIME_ZONE,
  weekday: 'short',
  month: 'short',
  day: 'numeric',
  year: 'numeric',
})

// en-CA formats dates as YYYY-MM-DD, the format <input type="date"> and the API use.
const isoDateFormat = new Intl.DateTimeFormat('en-CA', { timeZone: TIME_ZONE })

export const formatTime = (iso) => timeFormat.format(new Date(iso))
export const formatDate = (iso) => dateFormat.format(new Date(iso))

/** Today's date at the spaceport, as YYYY-MM-DD (may differ from the viewer's local date). */
export const todayInCentral = () => isoDateFormat.format(new Date())

/** Add days to a YYYY-MM-DD string. Done in UTC so DST can't shift the result. */
export function addDays(isoDate, days) {
  const d = new Date(`${isoDate}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

export function formatDuration(startIso, endIso) {
  const minutes = (new Date(endIso) - new Date(startIso)) / 60000
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return [h && `${h}h`, m && `${m}m`].filter(Boolean).join(' ')
}
