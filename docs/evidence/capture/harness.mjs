// Minimal Chrome DevTools Protocol harness used to capture genuine screenshots of
// the running FinSight app (local dev server or the deployed CloudFront site).
// No credentials live here: callers read them from git-ignored files.
import { spawn } from 'node:child_process'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'

const CHROME = process.env.CHROME_PATH ?? 'C:/Program Files/Google/Chrome/Application/chrome.exe'
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

export async function launch({ base, outDir, width = 1440, height = 900 }) {
  mkdirSync(outDir, { recursive: true })
  const port = 9500 + Math.floor(Math.random() * 400)
  const profile = join(tmpdir(), `finsight-cap-${port}-${Date.now()}`)
  const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, '--no-first-run',
    '--hide-scrollbars', '--force-color-profile=srgb', 'about:blank'], { stdio: 'ignore' })
  let wsUrl
  for (let i = 0; i < 100 && !wsUrl; i++) {
    await sleep(200)
    try { wsUrl = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((x) => x.type === 'page')?.webSocketDebuggerUrl } catch {}
  }
  if (!wsUrl) throw new Error('Chrome did not start')
  const ws = new WebSocket(wsUrl)
  await new Promise((r) => ws.addEventListener('open', r))
  let id = 0
  const pending = new Map()
  const consoleErrors = []
  const network = []
  ws.addEventListener('message', (ev) => {
    const m = JSON.parse(ev.data)
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) }
    if (m.method === 'Runtime.exceptionThrown') consoleErrors.push(m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text)
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') consoleErrors.push(m.params.args.map((a) => a.value ?? a.description).join(' '))
    if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') consoleErrors.push(`${m.params.entry.text} ${m.params.entry.url ?? ''}`)
    if (m.method === 'Network.responseReceived') {
      const r = m.params.response
      // Record method-less summary only (no headers, bodies or query strings - those can hold signed URLs/tokens).
      network.push({ status: r.status, url: r.url.split('?')[0], type: m.params.type })
    }
  })
  const send = (method, params = {}) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })) })
  const ev = async (expr) => {
    const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true })
    if (r.result?.exceptionDetails) throw new Error(r.result.exceptionDetails.exception?.description ?? 'eval error')
    return r.result?.result?.value
  }
  await send('Runtime.enable'); await send('Page.enable'); await send('DOM.enable'); await send('Log.enable'); await send('Network.enable')

  const state = { W: width, H: height, mobile: false }
  const metrics = (h = state.H) => send('Emulation.setDeviceMetricsOverride', { width: state.W, height: h, deviceScaleFactor: state.mobile ? 2 : 1.5, mobile: state.mobile })
  await metrics()
  const HELPERS = `window.__h = {
    set(el, v) { const proto = el.tagName === 'SELECT' ? HTMLSelectElement.prototype : el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v); el.dispatchEvent(new Event(el.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })) },
    q(s) { return document.querySelector(s) },
    btn(t, root = document) { return [...root.querySelectorAll('button, a')].find((b) => b.textContent.trim().includes(t) || b.getAttribute('aria-label') === t) },
    click(t, root) { const b = this.btn(t, root); if (!b) throw new Error('no button: ' + t); b.click() },
    text() { return document.body.innerText }, dialog() { return [...document.querySelectorAll('[role=dialog]')].pop() } };`
  const go = async (path, wait = 2600) => { await send('Page.navigate', { url: base + path }); await sleep(wait); await ev(HELPERS) }
  const waitFor = async (expr, ms = 10000) => {
    const t = Date.now()
    while (Date.now() - t < ms) { await ev(HELPERS); try { if (await ev(expr)) return true } catch {} await sleep(200) }
    return false
  }
  const shots = []
  const shot = async (name, { full = false, hideToasts = false, scrollTop = true } = {}) => {
    if (hideToasts) await ev(`document.querySelectorAll('[data-sonner-toaster]').forEach((t) => t.style.display = 'none')`)
    if (scrollTop) await ev(`window.scrollTo(0,0)`)
    if (full) { const h = await ev(`document.documentElement.scrollHeight`); await metrics(Math.min(h, 3400)); await sleep(500) }
    const r = await send('Page.captureScreenshot', { format: 'png' })
    writeFileSync(join(outDir, name + '.png'), Buffer.from(r.result.data, 'base64'))
    if (full) await metrics()
    shots.push({ name: name + '.png', at: new Date().toISOString() })
  }
  const setViewport = async (w, h, mobile = false) => { state.W = w; state.H = h; state.mobile = mobile; await metrics() }
  const upload = async (selector, file) => {
    const doc = await send('DOM.getDocument')
    const node = await send('DOM.querySelector', { nodeId: doc.result.root.nodeId, selector })
    await send('DOM.setFileInputFiles', { nodeId: node.result.nodeId, files: [file] })
  }
  const close = () => { try { ws.close() } catch {} chrome.kill() }
  return { send, ev, go, waitFor, shot, setViewport, upload, close, shots, consoleErrors, network, sleep }
}
