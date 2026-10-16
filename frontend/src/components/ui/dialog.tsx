import * as RDialog from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { cn } from '../../lib/utils'
import { Button } from './primitives'

export function Dialog({ open, onOpenChange, title, description, children, footer, size = 'md' }: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: ReactNode
  children?: ReactNode
  footer?: ReactNode
  size?: 'sm' | 'md' | 'lg'
}) {
  // Dialogs here are opened programmatically (no Radix Trigger), so remember the
  // element that had focus and return focus to it on close (keyboard users).
  const opener = useRef<HTMLElement | null>(null)
  useLayoutEffect(() => {
    if (open) opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
  }, [open])

  return (
    <RDialog.Root open={open} onOpenChange={onOpenChange}>
      <RDialog.Portal>
        {/* Frosted overlay; the dialog itself stays solid so forms and figures remain crisp. */}
        <RDialog.Overlay className="fs-overlay fixed inset-0 z-50 bg-[var(--overlay)] backdrop-blur-[3px]" />
        <RDialog.Content
          onCloseAutoFocus={(e) => {
            const el = opener.current
            if (el && el.isConnected && el !== document.body) {
              e.preventDefault()
              el.focus()
            }
          }}
          className={cn('fs-dialog fixed left-1/2 top-1/2 z-50 flex max-h-[90vh] w-[calc(100vw-2rem)] -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-float focus:outline-none',
            size === 'sm' && 'max-w-md', size === 'md' && 'max-w-lg', size === 'lg' && 'max-w-2xl')}
        >
          <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
            <div>
              <RDialog.Title className="text-base font-semibold text-text">{title}</RDialog.Title>
              {description ? <RDialog.Description className="mt-1 text-[13px] text-muted">{description}</RDialog.Description>
                : <RDialog.Description className="sr-only">{title}</RDialog.Description>}
            </div>
            <RDialog.Close asChild>
              <Button variant="ghost" size="icon" aria-label="Close"><X className="h-4 w-4" /></Button>
            </RDialog.Close>
          </div>
          {children && <div className="fs-scroll overflow-y-auto px-5 py-4">{children}</div>}
          {footer && <div className="flex flex-wrap justify-end gap-2 border-t border-border bg-surface-2/50 px-5 py-3">{footer}</div>}
        </RDialog.Content>
      </RDialog.Portal>
    </RDialog.Root>
  )
}

/** Confirmation for destructive actions. */
export function ConfirmDialog({ open, onOpenChange, title, description, confirmLabel = 'Delete', onConfirm, destructive = true, children }: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description: ReactNode
  confirmLabel?: string
  onConfirm: () => Promise<void> | void
  destructive?: boolean
  children?: ReactNode
}) {
  const [busy, setBusy] = useState(false)
  const run = async () => {
    setBusy(true)
    try {
      await onConfirm()
      onOpenChange(false)
    } finally {
      setBusy(false)
    }
  }
  return (
    <Dialog open={open} onOpenChange={(o) => !busy && onOpenChange(o)} title={title} description={description} size="sm"
      footer={<>
        <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>Cancel</Button>
        <Button variant={destructive ? 'danger' : 'primary'} onClick={run} loading={busy}>{confirmLabel}</Button>
      </>}>
      {children}
    </Dialog>
  )
}
