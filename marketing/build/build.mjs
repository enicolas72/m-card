// Assemble la page marketing en UN fichier HTML autonome (../index.html) :
// JS bundlé (three.js compris), polices, images, STL et captures de la
// console web, tout est embarqué. Usage : npm install && npm run build
// (STL : ./export-stl.sh au préalable si le boîtier a changé).
import { build } from 'esbuild';
import { readFileSync, readdirSync, writeFileSync, statSync } from 'node:fs';
import { basename, extname, join } from 'node:path';

const here = new URL('.', import.meta.url).pathname;
const p = (...parts) => join(here, ...parts);
const MIME = { '.jpg': 'image/jpeg', '.png': 'image/png', '.woff2': 'font/woff2' };

const dataUri = (file) =>
  `data:${MIME[extname(file)]};base64,${readFileSync(file).toString('base64')}`;
const dir = (d, ext) => readdirSync(p(d)).filter((f) => f.endsWith(ext)).sort();

// ---- ressources -------------------------------------------------------
const stl = Object.fromEntries(
  dir('stl', '.stl').map((f) => [basename(f, '.stl'), readFileSync(p('stl', f)).toString('base64')]));
const cards = Object.fromEntries(
  dir('cards', '.jpg').map((f) => [basename(f, '.jpg'), dataUri(p('cards', f))]));
const img = Object.fromEntries(
  readdirSync(p('img')).filter((f) => MIME[extname(f)])
    .map((f) => [basename(f, extname(f)), dataUri(p('img', f))]));

// Captures HTML réelles de l'interface (mode --fake), habillées d'un vrai
// morceau, découpées en { css, body } pour un rendu figé en Shadow DOM
// (`body` devient `.page`).
const consolePages = Object.fromEntries(dir('capture', '.html').map((f) => {
  const html = readFileSync(p('capture', f), 'utf8')
    .replace(' autofocus', '')
    .replace('<td>Piste 1</td>', '<td>Dreams</td>')
    .replace('</span> simulé</td>', '</span></td>')
  const css = html.match(/<style>([\s\S]*?)<\/style>/)[1].replace(/\bbody\s*\{/, '.page {');
  const body = html.match(/<body>([\s\S]*?)<\/body>/)[1];
  return [basename(f, '.html'), { css, body }];
}));

// ---- polices ------------------------------------------------------------
const font = (pkg, family, weight) => `@font-face{font-family:"${family}";font-weight:${weight};` +
  `font-style:normal;font-display:swap;src:url(${dataUri(
    p('node_modules/@fontsource', pkg, 'files', `${pkg}-latin-${weight}-normal.woff2`))}) format("woff2")}`;
const fonts = [
  font('space-grotesk', 'Space Grotesk', 500), font('space-grotesk', 'Space Grotesk', 700),
  font('inter', 'Inter', 400), font('inter', 'Inter', 600),
].join('\n');

// ---- JS -----------------------------------------------------------------
const bundle = await build({
  entryPoints: [p('src/app.js')], bundle: true, minify: true, format: 'iife',
  target: 'es2020', write: false, legalComments: 'none',
});
const js = bundle.outputFiles[0].text;

// ---- assemblage --------------------------------------------------------
const noCloseScript = (s) => s.replace(/<\/(script)/gi, '<\\/$1');
const assets = JSON.stringify({ stl, cards, img, console: consolePages }).replace(/<\//g, '<\\/');
const css = readFileSync(p('src/style.css'), 'utf8').replace('{{FONTS}}', fonts);
const html = readFileSync(p('src/index.html'), 'utf8')
  .replace(/\{\{img:([\w-]+)\}\}/g, (_, name) => {
    if (!img[name]) throw new Error(`image inconnue : ${name}`);
    return img[name];
  })
  .replace('{{CSS}}', () => css)
  .replace('{{ASSETS_JSON}}', () => assets)
  .replace('{{JS}}', () => noCloseScript(js));

const out = p('..', 'index.html');
writeFileSync(out, html);
console.log(`${out} — ${(statSync(out).size / 1024 / 1024).toFixed(2)} Mo`);
