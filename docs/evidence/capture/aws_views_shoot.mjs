// Screenshot the rendered AWS resource views (docs/evidence/06_aws_console/*.html) with headless Chrome.
import { readdirSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { launch } from './harness.mjs'

const DIR = resolve(import.meta.dirname, '../06_aws_console')
const b = await launch({ base: '', outDir: DIR, width: 1280, height: 800 })
for (const f of readdirSync(DIR).filter((x) => x.endsWith('.html'))) {
  await b.send('Page.navigate', { url: pathToFileURL(join(DIR, f)).href }); await b.sleep(700)
  await b.shot(f.replace('.html', ''), { full: true })
}
console.log(b.shots.length, 'views captured')
b.close()
