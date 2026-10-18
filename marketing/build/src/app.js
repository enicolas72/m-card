// Point d'entrée de la page : relie le rendu 3D, les deux LCD émulés, le
// sélecteur de cartes, la console web et les animations au défilement.
import { ALBUMS } from './albums.js';
import { Lcd, nowPlayingLines } from './lcd.js';
import { createDeviceScene } from './scene.js';
import { createMarquee } from './marquee.js';

const A = window.__ASSETS;
const cardUrl = (id) => A.cards[id];
const SCROLL_PERIOD_MS = 600;

// ---- LCD de l'appareil 3D + LCD grand format --------------------------
const heroLcd = new Lcd(document.createElement('canvas'), { scale: 6 });
const bigLcd = new Lcd(document.getElementById('lcdBig'), { scale: 8 });
setInterval(() => { heroLcd.tick(); bigLcd.tick(); }, SCROLL_PERIOD_MS);

function playLines(album, state = 'playing') {
  return nowPlayingLines(state, album.album, album.track, album.artist);
}

// ---- héros : scène 3D et sélecteur de cartes -------------------------
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
  // WebGL indisponible : on montre la photo du prototype à la place
  console.warn('WebGL unavailable', err);
  document.getElementById('device3d').innerHTML =
    `<img src="${A.img.IMG_0931}" alt="M-Card" style="width:100%;height:100%;object-fit:cover;border-radius:24px">`;
}
markPicker();
heroLcd.setLines(playLines(ALBUMS[0]));
restartCycle();

// ---- LCD grand format : un exemple d'affichage (titre long qui défile)
bigLcd.setLines(playLines(ALBUMS[1]));

// ---- bandeau de cartes défilant (canvas, cf. marquee.js) ------------
createMarquee(document.getElementById('marquee'), ALBUMS.map((a) => cardUrl(a.id)));

// ---- illustrations des étapes ----------------------------------------
document.getElementById('vizFan').innerHTML = ['krall', 'division_bell', 'norah']
  .map((id) => `<img src="${cardUrl(id)}" alt="">`).join('');
document.getElementById('vizSlotCard').src = cardUrl('jarre1');

// ---- console web : trois vues figées (captures réelles, Shadow DOM pour
// isoler leurs styles) en carrousel horizontal ------------------------------
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
  // albums.yaml : passer l'en-tête d'aide pour montrer directement les cartes
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
// défilement automatique, en pause au survol / au toucher
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

// ---- apparition au défilement ----------------------------------------
const io = new IntersectionObserver((entries) => {
  entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
}, { threshold: 0.15 });
document.querySelectorAll('.reveal').forEach((el) => io.observe(el));
