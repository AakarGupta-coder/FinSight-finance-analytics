// Genuine screenshots of the LOCAL FinSight app (Vite dev server + FastAPI, synthetic demo data).
// Usage: node docs/evidence/capture/local.mjs   (backend on :8000, frontend on :5173)
import { readFileSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { launch, sleep } from './harness.mjs'

const ROOT = resolve(import.meta.dirname, '../../..')
const EV = join(ROOT, 'docs/evidence')
const creds = Object.fromEntries(readFileSync(join(ROOT, 'backend/data/REPORT_DEMO_ACCOUNT.txt'), 'utf8').split('\n')
  .filter((l) => l.includes('=')).map((l) => { const i = l.indexOf('='); return [l.slice(0, i).trim(), l.slice(i + 1).trim()] }))
const RECEIPT = join(ROOT, 'docs/report_assets/generators/sample_receipt_generated.png')

const app = join(EV, '02_local_application'), design = join(EV, '03_frontend_design'), anim = join(EV, '04_animations')
const b = await launch({ base: 'http://localhost:5173', outDir: app })
const { ev, go, waitFor, send } = b
const shotIn = async (dir, name, opts) => {
  const r = await send('Page.captureScreenshot', { format: 'png' })
  if (opts?.full) { /* full-page handled by b.shot */ }
  writeFileSync(join(dir, name + '.png'), Buffer.from(r.result.data, 'base64'))
  b.shots.push({ name: `${dir.split(/[\\/]/).pop()}/${name}.png`, at: new Date().toISOString() })
}
const navClick = (href) => ev(`document.querySelector('aside a[href="${href}"]').click()`)
const hover = async (selector) => {
  const r = await ev(`(() => { const e = document.querySelector(${JSON.stringify(selector)}); const b = e.getBoundingClientRect(); return { x: b.x + b.width / 2, y: b.y + b.height / 2 } })()`)
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: r.x, y: r.y })
}

// ---- public pages
await go('/'); await ev(`localStorage.removeItem('theme')`); await go('/')
await b.shot('local_landing')
await go('/register'); await b.shot('local_registration')
await go('/login'); await b.shot('local_login')
// validation feedback on the sign-in form (empty submit)
await ev(`__h.q('form').requestSubmit()`); await sleep(120); await shotIn(anim, 'anim_form_validation_message')

// ---- sign in
await ev(`__h.set(__h.q('#email'), ${JSON.stringify(creds.email)}); __h.set(__h.q('#password'), ${JSON.stringify(creds.password)}); __h.q('form').requestSubmit()`)
await waitFor(`location.pathname === '/app' && __h.text().includes('Total spent')`, 15000)
// mid-entrance frame: KPI figures counting up, cards rising in
await sleep(140); await shotIn(anim, 'anim_dashboard_entrance_midframe')
await sleep(1800)
await b.shot('local_dashboard', { full: true })

// page transition mid-frame (client-side navigation) and settled page
await navClick('/app/budgets'); await sleep(110); await shotIn(anim, 'anim_page_transition_midframe')
await sleep(1600); await b.shot('local_budget_management', { full: true })
await shotIn(anim, 'anim_budget_progress_settled')

await navClick('/app/transactions'); await sleep(2200); await b.shot('local_expense_management')
// sidebar hover + keyboard focus indicator
await hover('aside a[href="/app/analytics"]'); await ev(`document.querySelector('aside a[href="/app/goals"]').focus()`); await sleep(250)
await shotIn(anim, 'anim_sidebar_active_hover_focus')
await ev(`document.activeElement.blur()`)
// dialog entrance mid-frame
await ev(`__h.q('main table tbody tr td button').click()`); await sleep(70); await shotIn(anim, 'anim_modal_opening_midframe')
await sleep(500); await shotIn(app, 'local_expense_detail_dialog')
await ev(`document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))`); await sleep(400)
// filters panel
await go('/app/transactions?category=food', 2500); await ev(`__h.click('Filters')`); await sleep(400); await shotIn(app, 'local_expense_filtering')

// expense creation form + validation
await go('/app/transactions/new', 2000)
await ev(`__h.q('main form').requestSubmit()`); await sleep(150); await shotIn(anim, 'anim_expense_form_validation')
await ev(`__h.set(__h.q('#amount'), '450'); __h.set(__h.q('#category'), 'food'); __h.set(__h.q('#description'), 'Team lunch'); __h.set(__h.q('#merchant'), 'Cafe Coffee Day')`)
await sleep(300); await b.shot('local_expense_creation')

await go('/app/analytics', 3200); await b.shot('local_financial_analytics', { full: true })
await go('/app/insights', 2800); await b.shot('local_financial_intelligence')
await go('/app/anomalies', 2800); await b.shot('local_anomaly_detection')

// receipt scanner: processing state, then the OCR review
await go('/app/receipts', 2500); await b.shot('local_receipt_scanner')
await b.upload('#receipt-file', RECEIPT); await sleep(600)
await ev(`__h.click('Scan receipt')`); await sleep(150); await shotIn(anim, 'anim_receipt_processing_state')
await waitFor(`__h.text().includes('Confirm expense details')`, 60000); await sleep(700)
await b.shot('local_receipt_ocr_review', { full: true })
// remove the unconfirmed test receipt again
await ev(`__h.click('Start over')`).catch(() => {})

await go('/app/simulator', 3500); await b.shot('local_whatif_simulator', { full: true })
await go('/app/assistant', 2200)
await ev(`__h.click('How much did I spend this month?')`); await sleep(60); await shotIn(anim, 'anim_assistant_typing')
await waitFor(`[...document.querySelectorAll('[aria-label=Conversation] p')].some((p) => /₹/.test(p.textContent))`)
await sleep(600); await b.shot('local_finance_assistant')
await go('/app/goals', 2800); await b.shot('local_savings_goals')
await shotIn(anim, 'anim_savings_progress_settled')
await go('/app/profile', 2200); await b.shot('local_profile')
await go('/app/settings', 2200); await b.shot('local_settings', { full: true })

// ---- design: themes + responsive
const designShot = async (name, full) => {
  if (full) { const h = await ev(`document.documentElement.scrollHeight`); await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: Math.min(h, 3400), deviceScaleFactor: 1.5, mobile: false }); await sleep(400) }
  await shotIn(design, name)
  if (full) await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1.5, mobile: false })
}
await go('/app', 3200); await designShot('design_dashboard_dark', true)
// theme switch mid-transition, then light
await ev(`__h.q('button[aria-label="Switch to light theme"]').click()`); await sleep(110); await shotIn(anim, 'anim_theme_switch_midframe')
await sleep(700); await designShot('design_dashboard_light', true)
await go('/app/transactions', 2500); await designShot('design_transactions_light')
await ev(`localStorage.removeItem('theme')`)
await b.setViewport(390, 844, true)
await go('/app', 3200); await designShot('design_mobile_dashboard')
await ev(`__h.q('button[aria-label="Open navigation"]').click()`); await sleep(90); await shotIn(anim, 'anim_mobile_drawer_opening_midframe')
await sleep(500); await designShot('design_mobile_navigation')

writeFileSync(join(EV, '09_testing/local_capture_run.json'), JSON.stringify({
  ranAt: new Date().toISOString(), shots: b.shots, consoleErrors: b.consoleErrors,
  failedRequests: b.network.filter((n) => n.status >= 400),
}, null, 1))
console.log(JSON.stringify({ shots: b.shots.length, consoleErrors: b.consoleErrors, failed: b.network.filter((n) => n.status >= 400) }, null, 1))
b.close()
