// Page entry point: wires the 3D rendering, both emulated LCDs, the card
// picker, the web console and the scroll animations together.
import { ALBUMS } from './albums.js';
import { Lcd, nowPlayingLines } from './lcd.js';
import { createDeviceScene } from './scene.js';
import { createMarquee } from './marquee.js';

const A = window.__ASSETS;
const cardUrl = (id) => A.cards[id];
const SCROLL_PERIOD_MS = 600;

// ---- 3D device LCD + large LCD ---------------------------------------
const heroLcd = new Lcd(document.createElement('canvas'), { scale: 6 });
const bigLcd = new Lcd(document.getElementById('lcdBig'), { scale: 8 });
setInterval(() => { heroLcd.tick(); bigLcd.tick(); }, SCROLL_PERIOD_MS);

function playLines(album, state = 'playing') {
  return nowPlayingLines(state, album.album, album.track, album.artist);
}

// ---- hero: 3D scene and card picker --------------------------------
let current = 0;
let scene = null;
const picker = document.getElementById('picker');
ALBUMS.forEach((album, i) => {
  const b = document.createElement('button');
  b.title = `${album.artist} — ${album.album}`;
  b.innerHTML = `<img src="${cardUrl(album.id)}" alt="">`;
  b.addEventListener('click', () => { selectCard(i); restartCycle(); });
  picker.appendChild(b);
});

function markPicker() {
  [...picker.children].forEach((b, i) => b.classList.toggle('on', i === current));
}

function selectCard(i) {
  current = (i + ALBUMS.length) % ALBUMS.length;
  markPicker();
  heroLcd.setLines(['.. loading', '', '', '']);
  const seated = () => heroLcd.setLines(playLines(ALBUMS[current]));
  if (scene) scene.showCard(current, seated); else seated();
}

let cycle = null;
function restartCycle() {
  clearInterval(cycle);
  cycle = setInterval(() => selectCard(current + 1), 7000);
}

try {
  scene = createDeviceScene(document.getElementById('device3d'), {
    stl: A.stl,
    cards: ALBUMS.map((a) => cardUrl(a.id)),
    lcd: heroLcd,
  });
} catch (err) {
  // WebGL unavailable: show the prototype photo instead
  console.warn('WebGL unavailable', err);
  document.getElementById('device3d').innerHTML =
    `<img src="${A.img.IMG_0931}" alt="M-Card" style="width:100%;height:100%;object-fit:cover;border-radius:24px">`;
}
markPicker();
heroLcd.setLines(playLines(ALBUMS[0]));
restartCycle();

// ---- large LCD: one sample screen (long title scrolling)
bigLcd.setLines(playLines(ALBUMS[1]));

// ---- scrolling card strip (canvas, see marquee.js) ----------------
createMarquee(document.getElementById('marquee'), ALBUMS.map((a) => cardUrl(a.id)));

// ---- step illustrations --------------------------------------------
document.getElementById('vizFan').innerHTML = ['krall', 'division_bell', 'norah']
  .map((id) => `<img src="${cardUrl(id)}" alt="">`).join('');
document.getElementById('vizSlotCard').src = cardUrl('jarre1');

// ---- web console: three frozen views (real captures, Shadow DOM to
// isolate their styles) in a horizontal carousel -----------------------------
const VIEWS = [
  { page: 'status', label: 'Status', url: 'mcard.local:8088/' },
  { page: 'config', label: 'Albums', url: 'mcard.local:8088/config/albums.yaml' },
  { page: 'search', label: 'Search', url: 'mcard.local:8088/search?q=jarre' },
];
const slides = document.getElementById('consoleSlides');
const dots = document.getElementById('consoleDots');
const url = document.getElementById('consoleUrl');
const FROZEN = '*{pointer-events:none!important}.page{margin-top:0!important;padding-top:2rem!important}';
VIEWS.forEach((v, i) => {
  const slide = document.createElement('div');
  slide.className = 'console-slide';
  const { css, body } = A.console[v.page];
  const root = slide.attachShadow({ mode: 'open' });
  root.innerHTML = `<style>${css}${FROZEN}</style><div class="page">${body}</div>`;
  slides.appendChild(slide);
  // albums.yaml: skip the help header to show the cards right away
  const ta = root.querySelector('textarea');
  if (ta) {
    const lines = ta.value.split('\n');
    const first = lines.findIndex((l) => l.startsWith('"'));
    if (first > 0) ta.scrollTop = (ta.scrollHeight / lines.length) * (first - 1);
  }
  const dot = document.createElement('button');
  dot.setAttribute('aria-label', v.label);
  dot.addEventListener('click', () => { goTo(i); restartAuto(); });
  dots.appendChild(dot);
});
let active = -1;
function setActive(i) {
  if (i === active) return;
  active = i;
  url.textContent = VIEWS[i].url;
  [...dots.children].forEach((d, k) => d.classList.toggle('on', k === i));
}
function goTo(i) { slides.scrollTo({ left: i * slides.clientWidth }); setActive(i); }
slides.addEventListener('scroll', () => {
  setActive(Math.round(slides.scrollLeft / slides.clientWidth));
}, { passive: true });
// auto-advance, paused on hover / touch
let auto = null, paused = false;
function restartAuto() {
  clearInterval(auto);
  auto = setInterval(() => { if (!paused) goTo((active + 1) % VIEWS.length); }, 5000);
}
slides.addEventListener('pointerenter', () => { paused = true; });
slides.addEventListener('pointerleave', () => { paused = false; });
slides.addEventListener('touchstart', () => { restartAuto(); }, { passive: true });
setActive(0);
restartAuto();

// ---- reveal on scroll -----------------------------------------------
const io = new IntersectionObserver((entries) => {
  entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
}, { threshold: 0.15 });
document.querySelectorAll('.reveal').forEach((el) => io.observe(el));
