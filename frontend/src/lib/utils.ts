import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

import { useEffect, useState } from 'react'
import { prefersReducedMotion } from './motion'

export type Theme = 'light' | 'dark' | 'system'

/** Dark is the default. Light (or following the OS) is chosen with the header toggle or Settings → Appearance. */
export function getTheme(): Theme {
  try {
    const t = localStorage.getItem('theme')
    return t === 'light' || t === 'system' ? t : 'dark'
  } catch {
    return 'dark'
  }
}

export function isDarkMode(): boolean {
  if (typeof document === 'undefined') return false
  return document.documentElement.classList.contains('dark')
}

let themeTimer = 0

export function applyTheme(theme: Theme) {
  try {
    if (theme === 'dark') localStorage.removeItem('theme')
    else localStorage.setItem('theme', theme)
  } catch {
    /* ignore */
  }
  const dark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
  const root = document.documentElement
  // Brief colour cross-fade on an explicit switch (not on first paint; skipped for reduced motion).
  if (root.classList.contains('dark') !== dark && !prefersReducedMotion()) {
    root.classList.add('theme-transition')
    window.clearTimeout(themeTimer)
    themeTimer = window.setTimeout(() => root.classList.remove('theme-transition'), 320)
  }
  root.classList.toggle('dark', dark)
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('themechange'))
  }
}

export function useCurrentTheme() {
  const [theme, setTheme] = useState<Theme>(getTheme())
  const [isDark, setIsDark] = useState<boolean>(() => isDarkMode())

  useEffect(() => {
    const update = () => {
      setTheme(getTheme())
      setIsDark(isDarkMode())
    }
    window.addEventListener('themechange', update)
    return () => window.removeEventListener('themechange', update)
  }, [])

  const toggleTheme = () => {
    const next: Theme = isDark ? 'light' : 'dark'
    applyTheme(next)
  }

  return { theme, isDark, toggleTheme }
}

/** Fixed category -> chart slot mapping: color follows the category, never its rank. */
const CATEGORY_SLOTS: Record<string, number> = {
  food: 1, groceries: 2, transportation: 3, shopping: 4, housing: 5, utilities: 6, entertainment: 7, subscriptions: 8,
}

export function categoryColor(category: string): string {
  const slot = CATEGORY_SLOTS[category]
  return slot ? `var(--series-${slot})` : 'var(--series-other)'
}

export function hasOwnSlot(category: string) {
  return category in CATEGORY_SLOTS
}
