import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { dataSignature, useChartAnimation, useCountUp } from './motion'

function mockReducedMotion(reduced: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: reduced && query.includes('reduce'),
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })) as unknown as typeof window.matchMedia
}

afterEach(() => {
  vi.useRealTimers()
})

describe('dataSignature', () => {
  it('is stable for equal values and changes when a value changes', () => {
    expect(dataSignature([1, 2, 3])).toBe(dataSignature([1, 2, 3]))
    expect(dataSignature([1, 2, 3])).not.toBe(dataSignature([1, 2, 4]))
    expect(dataSignature([1, 2, 3])).not.toBe(dataSignature([3, 2, 1]))
  })
})

describe('useCountUp', () => {
  it('returns the target immediately when the user prefers reduced motion', () => {
    mockReducedMotion(true)
    const { result } = renderHook(() => useCountUp(12345))
    expect(result.current).toBe(12345)
  })
})

describe('useChartAnimation', () => {
  it('animates on entry and after a data change, then switches off', () => {
    mockReducedMotion(false)
    vi.useFakeTimers()
    const { result, rerender } = renderHook(({ sig }) => useChartAnimation(sig, 500), { initialProps: { sig: 'a' } })
    expect(result.current).toBe(true)
    act(() => { vi.advanceTimersByTime(600) })
    expect(result.current).toBe(false)
    // Same data again (an unrelated re-render): no replay.
    rerender({ sig: 'a' })
    expect(result.current).toBe(false)
    // New data: animation enabled in the same render that receives it.
    rerender({ sig: 'b' })
    expect(result.current).toBe(true)
  })

  it('never animates under reduced motion', () => {
    mockReducedMotion(true)
    const { result } = renderHook(() => useChartAnimation('a'))
    expect(result.current).toBe(false)
  })
})
