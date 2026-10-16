// Money and date helpers. Amounts travel as integer minor units; conversion
// from user input is done on strings so no floating-point rounding occurs.

const EXPONENTS: Record<string, number> = { JPY: 0 }
export const exponentFor = (currency: string) => EXPONENTS[currency] ?? 2

const LOCALES: Record<string, string> = { INR: 'en-IN' }

const formatterCache = new Map<string, Intl.NumberFormat>()

function formatter(currency: string, compact: boolean, showFraction: boolean) {
  const key = `${currency}|${compact}|${showFraction}`
  let f = formatterCache.get(key)
  if (!f) {
    const exp = exponentFor(currency)
    f = new Intl.NumberFormat(LOCALES[currency] ?? 'en-US', {
      style: 'currency',
      currency,
      notation: compact ? 'compact' : 'standard',
      minimumFractionDigits: compact ? 0 : showFraction ? exp : 0,
      maximumFractionDigits: compact ? 1 : exp,
    })
    formatterCache.set(key, f)
  }
  return f
}

/** Format minor units as currency. Whole amounts omit ".00" unless `fraction` is true. */
export function money(minor: number | null | undefined, currency = 'INR', opts: { compact?: boolean; fraction?: boolean; round?: boolean } = {}) {
  if (minor === null || minor === undefined || Number.isNaN(minor)) return '—'
  const exp = exponentFor(currency)
  // Approximate figures (projections, allowances) are shown in whole units.
  if (opts.round) minor = Math.round(minor / 10 ** exp) * 10 ** exp
  const major = minor / 10 ** exp
  const hasFraction = minor % 10 ** exp !== 0
  return formatter(currency, !!opts.compact, opts.fraction ?? hasFraction).format(major)
}

/** Parse user input like "1,234.50" into minor units. Returns null when invalid. */
export function parseMoneyToMinor(input: string, currency = 'INR'): number | null {
  const exp = exponentFor(currency)
  const cleaned = input.replace(/[,\s₹$€£]/g, '').trim()
  if (!cleaned) return null
  const re = exp === 0 ? /^\d+$/ : new RegExp(`^\\d+(\\.\\d{1,${exp}})?$`)
  if (!re.test(cleaned)) return null
  const [whole, frac = ''] = cleaned.split('.')
  const minor = BigInt(whole) * 10n ** BigInt(exp) + BigInt((frac + '0'.repeat(exp)).slice(0, exp) || '0')
  if (minor > BigInt(Number.MAX_SAFE_INTEGER)) return null
  return Number(minor)
}

/** Minor units -> plain editable string, e.g. 123450 -> "1234.50". */
export function minorToInput(minor: number, currency = 'INR'): string {
  const exp = exponentFor(currency)
  if (exp === 0) return String(minor)
  const sign = minor < 0 ? '-' : ''
  const abs = Math.abs(minor)
  const whole = Math.floor(abs / 10 ** exp)
  const frac = String(abs % 10 ** exp).padStart(exp, '0')
  return `${sign}${whole}${frac === '0'.repeat(exp) ? '' : '.' + frac}`
}

export function pct(value: number | null | undefined, digits = 0) {
  if (value === null || value === undefined) return '—'
  return `${value.toFixed(digits)}%`
}

export function signedPct(value: number | null | undefined) {
  if (value === null || value === undefined) return '—'
  return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** "2026-10-05" -> "5 Oct 2026" (dates are calendar dates, no timezone shift). */
export function formatDate(iso: string | null | undefined, opts: { year?: boolean } = {}) {
  if (!iso) return '—'
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return `${d} ${MONTHS[m - 1]}${opts.year === false ? '' : ` ${y}`}`
}

export function formatMonth(month: string, short = false) {
  const [y, m] = month.split('-').map(Number)
  const full = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
  return `${short ? MONTHS[m - 1] : full[m - 1]} ${y}`
}

/** Timestamps (UTC ISO) shown in the user's timezone. */
export function formatDateTime(iso: string | null | undefined, timeZone?: string) {
  if (!iso) return '—'
  const value = iso.endsWith('Z') || /[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short', timeZone }).format(new Date(value))
}

/** Today's date (YYYY-MM-DD) in a given IANA timezone. */
export function todayIn(timeZone: string): string {
  try {
    return new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
  } catch {
    return new Date().toISOString().slice(0, 10)
  }
}

export function shiftMonth(month: string, delta: number) {
  const [y, m] = month.split('-').map(Number)
  const idx = y * 12 + (m - 1) + delta
  return `${Math.floor(idx / 12)}-${String((idx % 12) + 1).padStart(2, '0')}`
}

export function addDays(iso: string, days: number) {
  const d = new Date(`${iso}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

export function monthStart(iso: string) {
  return `${iso.slice(0, 7)}-01`
}

/** Calendar date of a UTC timestamp in the user's timezone, e.g. "16 Oct 2026". */
export function formatTimestampDate(iso: string | null | undefined, timeZone?: string) {
  if (!iso) return '—'
  const value = iso.endsWith('Z') || /[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`
  return new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone }).format(new Date(value))
}
