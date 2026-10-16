// Genuine screenshots + browser checks of the DEPLOYED FinSight site (CloudFront → API Gateway → Lambda,
// Amazon Cognito sign-in, receipt upload straight to the private S3 bucket).
// Usage: node docs/evidence/capture/live.mjs <WebUrl>
// Signs in as the synthetic live-test user A from the git-ignored backend/data/AWS_LIVE_TEST_ACCOUNTS.txt.
import { readFileSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { launch, sleep } from './harness.mjs'

const ROOT = resolve(import.meta.dirname, '../../..')
const EV = join(ROOT, 'docs/evidence')
const WEB = process.argv[2]
if (!WEB?.startsWith('https://')) throw new Error('usage: node live.mjs https://<distribution>.cloudfront.net')
const lines = readFileSync(join(ROOT, 'backend/data/AWS_LIVE_TEST_ACCOUNTS.txt'), 'utf8').split('\n').filter((l) => l.includes('='))
const kv = Object.fromEntries(lines.map((l) => { const i = l.indexOf('='); return [l.slice(0, i).trim(), l.slice(i + 1).trim()] })) // last write wins
const creds = { email: kv.user_a_email, password: kv.user_a_password }
const RECEIPT = join(ROOT, 'docs/report_assets/generators/sample_receipt_generated.png')
const out = join(EV, '08_live_application')

const b = await launch({ base: WEB, outDir: out })
const { ev, go, waitFor } = b
const checks = []
// Navigate, then wait until the lazily loaded page has rendered real content (not the Suspense spinner).
const goWait = async (path, expr = 'true', ms = 30000) => {
  await go(path, 1500)
  const ok = await waitFor(`!document.querySelector('main [role=status]')?.textContent?.includes('Loading') && !document.querySelector('main .skeleton') && (${expr})`, ms)
  await sleep(900)
  return ok
}
const check = (id, what, ok, detail = '') => { checks.push({ id, what, status: ok ? 'PASS' : 'FAIL', detail }); console.log(`${ok ? 'PASS' : 'FAIL'} ${id} ${what} ${detail}`) }

await go('/', 4000); await ev(`localStorage.removeItem('theme')`); await go('/', 3000)
check('UI-01', 'Live landing page renders', await ev(`__h.text().includes('FinSight')`)); await b.shot('live_landing')
// author attribution + About the author dialog (dark, then light, then mobile)
check('UI-22', 'Footer shows "Created by Aakar Gupta"', await ev(`/Created by\\s*Aakar Gupta/.test(document.querySelector('footer').innerText)`))
await ev(`window.scrollTo(0, document.body.scrollHeight)`); await sleep(400)
{ const r = await b.send('Page.captureScreenshot', { format: 'png' }); (await import('node:fs')).writeFileSync(join(out, 'live_landing_footer_credit.png'), Buffer.from(r.result.data, 'base64')); b.shots.push({ name: 'live_landing_footer_credit.png', at: new Date().toISOString() }) }
await ev(`window.scrollTo(0,0); __h.q('button[aria-label="About the author"]').click()`)
const aboutOk = await waitFor(`!!__h.dialog() && __h.dialog().innerText.includes('Aakar Gupta') && __h.dialog().innerText.includes('Vellore Institute of Technology, Chennai')`, 8000)
check('UI-23', 'About the author dialog opens from the "i" button with accurate content', aboutOk)
check('UI-24', 'About dialog states CloudFront is planned, not deployed', await ev(`__h.dialog().innerText.includes('CloudFront is planned and not yet enabled')`))
await sleep(500); await b.shot('live_about_author_dark', { scrollTop: false })
await ev(`document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))`)
check('UI-25', 'Escape closes the About dialog', await waitFor(`!__h.dialog()`, 5000))
await ev(`localStorage.setItem('theme', 'light')`); await go('/', 3000)
await ev(`__h.q('button[aria-label="About the author"]').click()`); await waitFor(`!!__h.dialog()`, 8000); await sleep(500)
await b.shot('live_about_author_light', { scrollTop: false }); await ev(`localStorage.removeItem('theme')`)
await b.setViewport(390, 844, true); await go('/', 3000)
check('UI-26', 'Landing + About dialog fit at 390px', await ev(`document.documentElement.scrollWidth <= window.innerWidth + 1`))
await ev(`__h.q('button[aria-label="About the author"]').click()`); await waitFor(`!!__h.dialog()`, 8000); await sleep(500)
check('UI-27', 'About dialog fits the mobile viewport', await ev(`(() => { const r = __h.dialog().getBoundingClientRect(); return r.left >= 0 && r.right <= window.innerWidth })()`))
await b.shot('live_about_author_mobile', { scrollTop: false })
await b.setViewport(1440, 900)
await go('/register', 3000); check('UI-02', 'Registration page renders', await ev(`!!__h.q('#name') && !!__h.q('#email')`)); await b.shot('live_registration')
await go('/login', 3000); await b.shot('live_login')

// Cognito sign-in through the real UI
await ev(`__h.set(__h.q('#email'), ${JSON.stringify(creds.email)}); __h.set(__h.q('#password'), ${JSON.stringify(creds.password)}); __h.q('form').requestSubmit()`)
const signedIn = await waitFor(`location.pathname === '/app' && __h.text().includes('Total spent')`, 25000)
check('UI-03', 'Cognito sign-in via the web app → dashboard', signedIn)
await sleep(2500)
check('UI-04', 'Profile chip shows the ID-token name, not a UUID', await ev(`__h.text().includes('Live Test A') && !/[0-9a-f]{8}-[0-9a-f]{4}-/.test(document.querySelector('header').innerText)`))
await b.shot('live_dashboard', { full: true })

check('UI-05', 'Transactions list loads from DynamoDB', await goWait('/app/transactions', `__h.text().includes('Weekly groceries')`)); await b.shot('live_expense_management')
// create an expense through the UI
await goWait('/app/transactions/new', `!!__h.q('#amount')`)
await ev(`__h.set(__h.q('#amount'), '320'); __h.set(__h.q('#category'), 'food'); __h.set(__h.q('#description'), 'Live UI test — dinner'); __h.set(__h.q('#merchant'), 'Swiggy')`)
await sleep(300); await b.shot('live_expense_creation_form')
await ev(`__h.q('main form').requestSubmit()`)
const saved = await waitFor(`location.pathname === '/app/transactions' && __h.text().includes('Live UI test — dinner')`, 20000)
check('UI-06', 'Expense created through the UI and listed', saved); await sleep(800); await b.shot('live_expense_workflow')

check('UI-07', 'Budgets page with live utilization', await goWait('/app/budgets', `__h.text().includes('Shopping')`)); await b.shot('live_budget_management', { full: true })
await goWait('/app/analytics', `!!document.querySelector('.recharts-surface')`); await b.shot('live_analytics', { full: true })
await goWait('/app/insights'); await b.shot('live_financial_insights')
await goWait('/app/anomalies'); await b.shot('live_anomaly_detection')

// receipt: browser → presigned POST → private S3 → container OCR → review
await goWait('/app/receipts', `!!__h.q('#receipt-file')`)
await b.upload('#receipt-file', RECEIPT); await sleep(700)
await ev(`__h.click('Scan receipt')`); await sleep(400); await b.shot('live_receipt_processing')
const reviewed = await waitFor(`__h.text().includes('Confirm expense details')`, 90000)
check('UI-08', 'Receipt uploaded to S3 from the browser and read by OCR Lambda', reviewed)
await sleep(800); await b.shot('live_receipt_review', { full: true })
const imgShown = await ev(`(() => { const i = [...document.querySelectorAll('img')].find((x) => x.alt?.toLowerCase().includes('receipt')); return !!i && i.complete && i.naturalWidth > 0 })()`)
check('UI-09', 'Receipt preview image rendered', imgShown)

await goWait('/app/simulator', `__h.text().includes('Comparison')`); await b.shot('live_whatif_simulator', { full: true })
await goWait('/app/assistant', `!!__h.btn('How much did I spend this month?')`)
await ev(`__h.click('How much did I spend this month?')`)
check('UI-10', 'Assistant answers from live data', await waitFor(`[...document.querySelectorAll('[aria-label=Conversation] p')].some((p) => /₹/.test(p.textContent))`, 20000))
await sleep(600); await b.shot('live_finance_assistant')
check('UI-11', 'Savings goal shown', await goWait('/app/goals', `__h.text().includes('Emergency fund')`)); await b.shot('live_savings_goals')
await goWait('/app/profile', `__h.text().includes('Personal details')`); check('UI-12', 'Profile shows Cognito account', await ev(`__h.text().includes('Amazon Cognito account')`)); await b.shot('live_profile')
await goWait('/app/settings'); await b.shot('live_settings', { full: true })
await go('/app/does-not-exist', 3000); check('UI-13', 'In-app 404 route', await ev(`/not found|doesn.t exist|404/i.test(__h.text())`))

// theme + responsive
await go('/app', 4000)
await ev(`__h.q('button[aria-label="Switch to light theme"]').click()`); await sleep(900)
check('UI-14', 'Theme switch to light', await ev(`!document.documentElement.classList.contains('dark')`)); await b.shot('live_dashboard_light', { full: true })
await go('/app', 4000); check('UI-15', 'Light theme persists after reload', await ev(`!document.documentElement.classList.contains('dark')`))
await ev(`localStorage.removeItem('theme')`)
await b.setViewport(390, 844, true); await go('/app', 4500)
check('UI-16', 'No horizontal overflow at 390px', await ev(`document.documentElement.scrollWidth <= window.innerWidth + 1`)); await b.shot('live_mobile_dashboard')
await ev(`__h.q('button[aria-label="Open navigation"]').click()`); await sleep(700); await b.shot('live_mobile_navigation')
await b.setViewport(1440, 900)

// sign out
await go('/app', 3500); await ev(`__h.q('button[aria-label="Sign out"]').click()`)
check('UI-17', 'Sign out returns to login and clears the session', await waitFor(`location.pathname === '/login' || location.pathname === '/'`, 10000) && await ev(`Object.keys(sessionStorage).length === 0 || !JSON.stringify(sessionStorage).includes('accessToken')`))
await go('/app', 3000); check('UI-18', 'Protected route redirects to login after sign-out', await ev(`location.pathname === '/login'`))

const failed = b.network.filter((n) => n.status >= 400 && !n.url.includes('cognito-idp'))
check('UI-19', 'No browser console errors during the run', b.consoleErrors.length === 0, `${b.consoleErrors.length} error(s)`)
check('UI-20', 'No failed network requests (except expected Cognito sign-out)', failed.length === 0, JSON.stringify(failed.slice(0, 5)))
check('UI-21', 'No mixed content (all requests https)', b.network.every((n) => n.url.startsWith('https://') || n.url.startsWith('data:') || n.url.startsWith('blob:')))
writeFileSync(join(EV, '09_testing/live_browser_results.json'), JSON.stringify({ ranAt: new Date().toISOString(), web: WEB, checks, shots: b.shots, consoleErrors: b.consoleErrors, failedRequests: failed }, null, 1))
console.log(`${checks.filter((c) => c.status === 'PASS').length}/${checks.length} browser checks passed`)
b.close()
