import {
  Car, Clapperboard, GraduationCap, HeartPulse, House, Plane, Receipt, Repeat, ShoppingBag, ShoppingBasket, UtensilsCrossed, Zap,
  type LucideIcon,
} from 'lucide-react'
import { categoryColor, cn } from '../lib/utils'

const ICONS: Record<string, LucideIcon> = {
  food: UtensilsCrossed, groceries: ShoppingBasket, transportation: Car, education: GraduationCap, healthcare: HeartPulse,
  housing: House, utilities: Zap, shopping: ShoppingBag, entertainment: Clapperboard, travel: Plane, subscriptions: Repeat,
}

/** Round icon tile for a transaction's category (activity lists). Custom categories use a receipt icon. */
export function CategoryIcon({ category, className }: { category: string; className?: string }) {
  const Icon = ICONS[category] ?? Receipt
  return (
    <span className={cn('relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border bg-surface-3 text-text', className)} aria-hidden>
      <Icon className="h-4 w-4" />
      <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-surface" style={{ background: categoryColor(category) }} />
    </span>
  )
}
