import { describe, expect, it } from 'vitest'
import { addDays, formatDate, formatTimestampDate, minorToInput, money, parseMoneyToMinor, shiftMonth } from './format'

describe('parseMoneyToMinor', () => {
  it('parses exact decimal amounts without floating-point drift', () => {
    expect(parseMoneyToMinor('1,234.50')).toBe(123450)
    expect(parseMoneyToMinor('0.10')).toBe(10)
    expect(parseMoneyToMinor('19.99')).toBe(1999)
    expect(parseMoneyToMinor('₹ 500')).toBe(50000)
    expect(parseMoneyToMinor('0.1')! + parseMoneyToMinor('0.2')!).toBe(parseMoneyToMinor('0.3'))
  })

  it('rejects invalid input', () => {
    for (const bad of ['', 'abc', '1.234', '-5', '1e5', '1.2.3']) expect(parseMoneyToMinor(bad)).toBeNull()
  })

  it('respects zero-decimal currencies', () => {
    expect(parseMoneyToMinor('500', 'JPY')).toBe(500)
    expect(parseMoneyToMinor('500.5', 'JPY')).toBeNull()
  })
})

describe('money', () => {
  it('formats INR with Indian grouping', () => {
    expect(money(12345678)).toBe('₹1,23,456.78')
    expect(money(50000)).toBe('₹500')
  })
  it('rounds approximate figures to whole units on request', () => {
    expect(money(9924753, 'INR', { round: true })).toBe('₹99,248')
  })
  it('shows a dash for missing values', () => {
    expect(money(null)).toBe('—')
  })
})

describe('helpers', () => {
  it('round-trips minor units to editable input', () => {
    expect(minorToInput(123450)).toBe('1234.50')
    expect(minorToInput(50000)).toBe('500')
  })
  it('shows timestamps as dates in the user timezone', () => {
    // 20:00 UTC on 15 Oct is already 16 Oct in India.
    expect(formatTimestampDate('2026-10-15T20:00:00', 'Asia/Kolkata')).toBe('16 Oct 2026')
    expect(formatTimestampDate('2026-10-15T20:00:00Z', 'UTC')).toBe('15 Oct 2026')
  })
  it('handles calendar math', () => {
    expect(shiftMonth('2026-01', -1)).toBe('2025-12')
    expect(addDays('2026-02-28', 1)).toBe('2026-03-01')
    expect(formatDate('2026-10-05')).toBe('5 Oct 2026')
  })
})
