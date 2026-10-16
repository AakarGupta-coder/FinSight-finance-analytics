// Motion helpers. All animation in FinSight is CSS-first (see the "motion"
// section of index.css); these hooks cover the few cases CSS cannot: counting
// figures, and deciding when charts should animate. Every helper honours the
// operating-system "reduce motion" preference.

import { useEffect, useRef, useState } from 'react'

const QUERY = '(prefers-reduced-motion: reduce)'

export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia(QUERY).matches
}

export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(prefersReducedMotion)
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    const mq = window.matchMedia(QUERY)
    const update = () => setReduced(mq.matches)
    mq.addEventListener?.('change', update)
    return () => mq.removeEventListener?.('change', update)
  }, [])
  return reduced
}

const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3)

/**
 * Animate a number from its previous value to `target` (first render: from 0).
 * Restarts only when `target` itself changes, so unrelated re-renders never
 * replay the animation. Returns the final value immediately under reduced motion.
 */
export function useCountUp(target: number, duration = 650): number {
  const reduced = usePrefersReducedMotion()
  const [value, setValue] = useState(reduced ? target : 0)
  const valueRef = useRef(value)
  valueRef.current = value

  useEffect(() => {
    if (reduced || !Number.isFinite(target)) {
      setValue(target)
      return
    }
    const from = valueRef.current
    if (from === target) return
    let frame = 0
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      setValue(from + (target - from) * easeOutCubic(t))
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [target, duration, reduced])

  return value
}

/**
 * Whether a chart should animate right now: during its first entrance and for
 * a short window after its data really changes (`signature`), never on
 * unrelated re-renders (Recharts replays its animation whenever it receives a
 * new data array, even with identical values).
 */
export function useChartAnimation(signature: string, windowMs = 900): boolean {
  const reduced = usePrefersReducedMotion()
  const [window_, setWindow] = useState(() => ({ signature, until: Date.now() + windowMs }))
  // Derived during render (not in an effect) so the very render that receives
  // new data already has animation enabled; Recharts only animates on data change.
  if (window_.signature !== signature) setWindow({ signature, until: Date.now() + windowMs })
  const [, setTick] = useState(0)
  useEffect(() => {
    const remaining = window_.until - Date.now()
    if (remaining <= 0) return
    const id = setTimeout(() => setTick((t) => t + 1), remaining + 20)
    return () => clearTimeout(id)
  }, [window_])
  return !reduced && Date.now() < window_.until
}

/** Compact, order-sensitive fingerprint of chart values for useChartAnimation. */
export function dataSignature(values: (number | null | undefined)[]): string {
  let sum = 0
  for (let i = 0; i < values.length; i++) sum = (sum * 31 + (values[i] ?? 0)) % 1_000_000_007
  return `${values.length}:${sum}`
}
