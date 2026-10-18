// Scrolling strip of cards, drawn on a 2D <canvas>.
// A CSS animation (translateX on a long strip of images) lost pieces in
// Safari next to the 3D scene's WebGL context: here there is no animated
// layer, the browser only has one image to display.

const CARD_RATIO = 674 / 420;   // artwork height / width
const SPEED = 28;               // CSS px per second
const TILT = -3 * Math.PI / 180;

// pre-render a card (rounded corners, shadow, outline): the blurred shadow
// is expensive, so it is computed only once per card and size
function renderCard(img, w, dpr) {
  const h = w * CARD_RATIO, pad = 30;
  const c = document.createElement('canvas');
  c.width = Math.ceil((w + 2 * pad) * dpr);
  c.height = Math.ceil((h + 2 * pad) * dpr);
  const ctx = c.getContext('2d');
  ctx.scale(dpr, dpr);
  const r = w * 0.067;
  const path = () => { ctx.beginPath(); ctx.roundRect(pad, pad, w, h, r); };
  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,0.75)';
  ctx.shadowBlur = 26;
  ctx.shadowOffsetY = 14;
  path(); ctx.fillStyle = '#000'; ctx.fill();
  ctx.restore();
  ctx.save(); path(); ctx.clip();
  ctx.drawImage(img, pad, pad, w, h);
  ctx.restore();
  path(); ctx.strokeStyle = 'rgba(255,255,255,0.07)'; ctx.lineWidth = 1; ctx.stroke();
  return { canvas: c, pad };
}

export function createMarquee(canvas, urls, { bg = '#120d0c' } = {}) {
  const ctx = canvas.getContext('2d');
  const images = urls.map((u) => { const i = new Image(); i.src = u; return i; });
  let sprites = [], cardW = 150, gap = 22, dpr = 1, width = 0, height = 0;
  let offset = 0, last = 0, running = false;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  function layout() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = canvas.clientWidth;
    cardW = width < 640 ? 110 : 150;
    height = Math.ceil(cardW * CARD_RATIO + 90);
    canvas.style.height = `${height}px`;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    sprites = images.every((i) => i.complete && i.naturalWidth)
      ? images.map((i) => renderCard(i, cardW, dpr)) : [];
    draw();
  }

  function draw() {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!sprites.length) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.save();
    ctx.translate(width / 2, height / 2);
    ctx.rotate(TILT);
    const step = cardW + gap, loop = step * sprites.length;
    const span = width * 1.1;   // a bit wider: the tilt uncovers the corners
    let x = -span / 2 - (offset % loop);
    let k = 0;
    while (x < span / 2 + step) {
      const s = sprites[k % sprites.length];
      ctx.drawImage(s.canvas, x - s.pad, -cardW * CARD_RATIO / 2 - s.pad,
        s.canvas.width / dpr, s.canvas.height / dpr);
      x += step; k++;
    }
    ctx.restore();
    // edges faded into the background color
    const fade = width * 0.12;
    for (const [x0, x1] of [[0, fade], [width, width - fade]]) {
      const g = ctx.createLinearGradient(x0, 0, x1, 0);
      g.addColorStop(0, bg); g.addColorStop(1, 'rgba(18,13,12,0)');
      ctx.fillStyle = g;
      ctx.fillRect(Math.min(x0, x1), 0, fade, height);
    }
  }

  function frame(now) {
    if (!running) return;
    if (last) offset += SPEED * Math.min(0.1, (now - last) / 1000);
    last = now;
    draw();
    requestAnimationFrame(frame);
  }

  Promise.all(images.map((i) => i.decode().catch(() => {}))).then(layout);
  new ResizeObserver(layout).observe(canvas);
  new IntersectionObserver(([e]) => {
    const was = running;
    running = e.isIntersecting && !reduced;
    if (running && !was) { last = 0; requestAnimationFrame(frame); }
  }).observe(canvas);
}
