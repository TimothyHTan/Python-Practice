// The helper chat: opened by clicking the 3D gem on the practice page. It sees the current problem
// and your code, keeps one conversation per problem, and its code blocks can be inserted into the editor.
import { openShell, closeShell, pearlPoint, setThinking, flash } from './badge.js?v=5';
import { openNoteMenu } from './addnote.js?v=5';
import { functionName } from './pyblocks.js?v=5';

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const MAX_SEND = 14000; // characters of conversation sent along (the server allows 20000 with the problem)
const STARTERS = [
  ['Explain this problem', 'Explain what this problem wants, in simple steps. Don\'t give the code yet.'],
  ['Give me a hint', 'Give me one hint for the next step, based on my code.'],
  ['What\'s wrong with my code?', 'Look at my code and tell me what is wrong or missing.'],
  ['Add a helper function', 'Add a helper function to my code that '],
  ['Comment my code', 'Add short comments to my code that explain each part. Give back the whole file.'],
];

const gem = document.getElementById('badge');
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');

const panel = document.createElement('section');
panel.className = 'helper';
panel.id = 'helper';
panel.hidden = true;
panel.setAttribute('role', 'dialog');
panel.setAttribute('aria-label', 'Python helper');
panel.innerHTML = `
  <div class="helper-sheen" id="helper-sheen" aria-hidden="true"></div>
  <header class="helper-head">
    <span class="helper-gem" aria-hidden="true"></span>
    <div class="helper-title"><h2>Helper</h2><p id="helper-context"></p></div>
    <button class="key" type="button" id="helper-clear" title="Start a new conversation for this problem">New chat</button>
    <button class="key" type="button" id="helper-close" aria-label="Close the helper">Esc</button>
  </header>
  <div class="helper-settings">
    <span id="helper-route" title="Where the helper's answers come from">AI</span>
    <label>Model <select id="helper-model"></select></label>
    <label>Effort <select id="helper-effort"></select></label>
  </div>
  <ol class="helper-log" id="helper-log" aria-live="polite"></ol>
  <form class="helper-form" id="helper-form">
    <label class="sr-only" for="helper-input">Message the helper</label>
    <div class="helper-attach" id="helper-attach" hidden></div>
    <textarea id="helper-input" rows="2" placeholder="Ask anything, or: add a function that checks if a number is prime"></textarea>
    <div class="helper-send-keys">
      <button class="key" type="button" id="helper-pick" aria-label="Attach a picture" title="Attach a picture (you can also paste or drop one)"><svg aria-hidden="true" viewBox="0 0 24 24" width="16" height="16"><path d="M21 11.5 12.5 20a5 5 0 0 1-7-7l9-9a3.5 3.5 0 0 1 5 5l-9 9a2 2 0 0 1-3-3l8-8" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
      <button class="key go" type="submit" id="helper-send">Send</button>
    </div>
    <input type="file" id="helper-file" accept="image/png,image/jpeg,image/gif,image/webp" multiple hidden>
    <p class="helper-foot">Enter sends, Shift+Enter makes a new line. Paste or drop pictures to show the helper. Esc or Q (outside the text box) closes.</p>
  </form>`;
document.body.append(panel);
const $ = (id) => panel.querySelector('#' + id);

let ctx = null; // set by initHelper
let busy = false;
const key = () => `vw.chat.${ctx.problem().id}`;
const load = () => JSON.parse(localStorage.getItem(key()) ?? '[]');
const save = (log) => localStorage.setItem(key(), JSON.stringify(log.slice(-40)));

/* Rendering: ```code``` blocks get Insert/Copy keys; `inline` code; **bold**; the rest keeps its line breaks. */
function renderText(text) {
  const parts = text.split(/```(?:python|py)?\n?([\s\S]*?)```/g);
  return parts.map((part, i) => {
    if (i % 2) {
      const code = part.replace(/\n$/, '');
      const fn = functionName(code);
      const swap = fn && ctx.hasFunction(fn) ? `<button class="key go" type="button" data-replace-fn title="Swap your ${esc(fn)}() for this one">Replace ${esc(fn)}()</button>` : '';
      return `<div class="helper-code"><pre class="cm-s-vw code-view"><code>${highlight(code)}</code></pre>
        <div class="helper-code-keys">${swap}<button class="key ${swap ? '' : 'go'}" type="button" data-insert>Insert at cursor</button>
        <button class="key" type="button" data-copy>Copy</button>
        <button class="key" type="button" data-replace title="Replace everything in main.py with this">Replace my code</button></div></div>`;
    }
    const html = esc(part.trim()).replace(/`([^`\n]+)`/g, '<code>$1</code>').replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
    return html ? `<p>${html}</p>` : '';
  }).join('');
}

function highlight(code) {
  const CM = window.CodeMirror;
  if (!CM?.runMode) return esc(code);
  const out = [];
  CM.runMode(code, 'python', (text, style) => out.push(style ? `<span class="cm-${style.replace(/ +/g, ' cm-')}">${esc(text)}</span>` : esc(text)));
  return out.join('');
}

function render(pending) {
  const log = load();
  $('helper-context').textContent = `Sees: ${ctx.problem().title} and your code`;
  $('helper-model').value = ctx.modelSelect.value; // the tab may have set them without a change event
  $('helper-effort').value = ctx.effortSelect.value;
  $('helper-log').innerHTML = log.length || pending
    ? log.map((m, i) => `<li class="bubble ${m.role === 'user' ? 'me' : 'bot'}${m.error ? ' error' : ''}">${m.role === 'user'
        ? `${m.images?.length ? `<div class="bubble-images">${m.images.map((src) => `<img src="${esc(src)}" alt="Picture you sent">`).join('')}</div>` : ''}<p>${esc(m.text)}</p>`
        : renderText(m.text) + (m.error ? '' : `<div class="bubble-actions"><button class="key" type="button" data-note="${i}">Add to notes</button></div>`)}</li>`).join('')
      + (pending ? '<li class="bubble bot thinking"><span class="dots" aria-label="Thinking"><i></i><i></i><i></i></span><span>Thinking… usually 5 to 30 seconds</span></li>' : '')
    : `<li class="helper-empty"><p>Ask about this problem, or have the helper add code to your file.</p>
        <div class="helper-starters">${STARTERS.map(([label, text]) => `<button class="key" type="button" data-start="${esc(text)}">${esc(label)}</button>`).join('')}</div></li>`;
  $('helper-log').scrollTop = $('helper-log').scrollHeight;
}

// The conversation as text, newest last, trimmed from the oldest end to fit.
function transcript(log) {
  let out = '';
  for (let i = log.length - 1; i >= 0; i--) {
    const pics = log[i].images?.length ? ` [sent ${log[i].images.length} picture(s)]` : '';
    const line = `${log[i].role === 'user' ? 'STUDENT' : 'HELPER'}: ${log[i].text}${pics}\n\n`;
    if (out.length + line.length > MAX_SEND) break;
    out = line + out;
  }
  return out;
}

async function send(text) {
  text = text.trim();
  if ((!text && !attached.length) || busy) return;
  const pics = attached.splice(0);
  renderAttach();
  text ||= 'Look at this picture.';
  const problemId = ctx.problem().id; // the answer goes to this problem even if you switch meanwhile
  const k = `vw.chat.${problemId}`;
  const log = [...load(), { role: 'user', text, images: pics.map((p) => p.thumb) }];
  save(log);
  busy = true;
  $('helper-send').disabled = true;
  setThinking(true);
  render(true);
  const problem = `${ctx.problemText()}\n\nSTUDENT'S CURRENT CODE:\n${ctx.code() || '(empty)'}`.slice(0, 5500);
  let reply;
  try {
    const res = await fetch('/api/ai', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind: 'chat', problem, text: transcript(log), model: ctx.model(), effort: ctx.effort(),
        images: pics.map(({ media_type, data }) => ({ media_type, data })) }),
    });
    const data = await res.json().catch(() => ({}));
    reply = res.ok ? { role: 'helper', text: data.reply } : { role: 'helper', error: true, text: data.error ?? `The helper failed (${res.status}).` };
  } catch {
    reply = { role: 'helper', error: true, text: 'The local server is not running. Start it with site\\start.bat, then try again.' };
  }
  localStorage.setItem(k, JSON.stringify([...JSON.parse(localStorage.getItem(k) ?? '[]'), reply].slice(-40)));
  busy = false;
  $('helper-send').disabled = false;
  setThinking(false);
  if (!reply.error) flash(true);
  if (!panel.hidden && ctx.problem().id === problemId) render(false);
}

/* Opening: the shell opens, then the chat grows out of the pearl as an expanding circle with a pearly sheen.
   Closing: the chat unwinds (spins smaller) back into the pearl, then the shell shuts. */

// The pearl's position inside the panel, and a radius that covers the whole panel from there.
function fromPearl() {
  const pt = pearlPoint();
  const r = panel.getBoundingClientRect();
  const x = pt.x - r.left, y = pt.y - r.top;
  const radius = Math.hypot(Math.max(x, r.width - x), Math.max(y, r.height - y)) + 20;
  return { x, y, radius };
}

let opening = null;
let closing = null;
export function openHelper(prefill) {
  if (!panel.hidden) { $('helper-input').focus(); return; }
  if (closing || opening) return;
  gem.setAttribute('aria-expanded', 'true');
  opening = (async () => {
    await openShell();
    panel.hidden = false; // covers the shell; it grows out of the pearl underneath
    render(busy);
    if (!reduceMotion.matches) {
      const { x, y, radius } = fromPearl();
      panel.style.transformOrigin = `${x}px ${y}px`;
      panel.animate([
        { clipPath: `circle(14px at ${x}px ${y}px)`, transform: 'scale(.96)' },
        { clipPath: `circle(${radius}px at ${x}px ${y}px)`, transform: 'scale(1)' },
      ], { duration: 420, easing: 'cubic-bezier(.3, .7, .2, 1)' });
      $('helper-sheen').style.background = `radial-gradient(circle at ${x}px ${y}px, rgba(255, 248, 235, .95), rgba(214, 228, 255, .55) 35%, rgba(255, 255, 255, 0) 75%)`;
      $('helper-sheen').animate({ opacity: [1, 0] }, { duration: 520, easing: 'ease-out', fill: 'both' });
      [...panel.children].filter((el) => el.id !== 'helper-sheen').forEach((el, i) =>
        el.animate({ opacity: [0, 1], transform: ['translateY(12px)', 'none'] }, { duration: 240, delay: 180 + i * 45, easing: 'ease-out', fill: 'backwards' }));
    }
    if (prefill) $('helper-input').value = prefill;
    $('helper-input').focus();
    opening = null;
  })();
}

export function closeHelper() {
  if (panel.hidden || opening) return Promise.resolve();
  closing ??= (async () => {
    if (!reduceMotion.matches) {
      const { x, y, radius } = fromPearl();
      panel.style.transformOrigin = `${x}px ${y}px`;
      [...panel.children].forEach((el) => el.animate({ opacity: [1, 0] }, { duration: 180, fill: 'forwards' }));
      const unwind = panel.animate([
        { clipPath: `circle(${radius}px at ${x}px ${y}px)`, transform: 'rotate(0deg) scale(1)', borderRadius: '18px' },
        { offset: 0.35, clipPath: `circle(${radius * 0.55}px at ${x}px ${y}px)`, transform: 'rotate(-70deg) scale(.82)' },
        { clipPath: `circle(10px at ${x}px ${y}px)`, transform: 'rotate(-300deg) scale(.08)', borderRadius: '50%' },
      ], { duration: 620, easing: 'cubic-bezier(.5, 0, .75, .4)', fill: 'forwards' });
      await unwind.finished;
      panel.getAnimations({ subtree: true }).forEach((a) => a.cancel());
    }
    panel.hidden = true;
    closeShell();
    gem.setAttribute('aria-expanded', 'false');
    gem.focus({ preventScroll: true });
    closing = null;
  })();
  return closing;
}

export function initHelper(context) {
  ctx = context;
  // The server says which CLI answers (Claude Code or Codex, picked on the Settings page) and the models it offers.
  fetch('/api/ai-info').then((r) => r.json()).then(({ route, name, models }) => {
    $('helper-route').textContent = name ?? 'AI';
    $('helper-route').title = route;
    ctx.modelSelect.innerHTML = '<option value="">Default</option>'
      // An older server sends plain ids instead of [id, label] pairs.
      + models.map((m) => (Array.isArray(m) ? m : [m, m])).map(([id, label]) => `<option value="${esc(id)}">${esc(label)}</option>`).join('');
    ctx.modelSelect.value = JSON.parse(localStorage.getItem('vw.ai.model') ?? '""');
    // A saved model from the other CLI (or one this account can't run) isn't listed: show and use "Default".
    if (ctx.modelSelect.selectedIndex < 0) ctx.modelSelect.value = '';
    $('helper-model').innerHTML = ctx.modelSelect.innerHTML;
    $('helper-model').value = ctx.modelSelect.value;
  }).catch(() => {});
  // Same model/effort choices (and saved setting) as the Pseudocode & AI tab, kept in sync both ways.
  for (const [mine, theirs] of [[$('helper-model'), ctx.modelSelect], [$('helper-effort'), ctx.effortSelect]]) {
    mine.innerHTML = theirs.innerHTML;
    mine.value = theirs.value;
    mine.addEventListener('change', () => { theirs.value = mine.value; theirs.dispatchEvent(new Event('change')); });
    theirs.addEventListener('change', () => { mine.value = theirs.value; });
  }
  gem.addEventListener('click', () => (panel.hidden ? openHelper() : closeHelper()));
  addEventListener('hashchange', () => { if (!panel.hidden) render(busy); }); // switched problem
}

$('helper-close').addEventListener('click', () => closeHelper());
$('helper-clear').addEventListener('click', () => {
  if (busy || !load().length || !confirm('Start a new conversation for this problem? The old one is deleted.')) return;
  localStorage.removeItem(key());
  render(false);
});
$('helper-form').addEventListener('submit', (e) => {
  e.preventDefault();
  const text = $('helper-input').value;
  $('helper-input').value = '';
  send(text);
});
$('helper-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); $('helper-form').requestSubmit(); }
});
panel.addEventListener('keydown', (e) => { if (e.key === 'Escape') { e.preventDefault(); closeHelper(); } });
// Q closes too, unless you're typing somewhere.
addEventListener('keydown', (e) => {
  if (panel.hidden || e.ctrlKey || e.metaKey || e.altKey || e.key.toLowerCase() !== 'q') return;
  if (e.target.closest?.('input, textarea, select, [contenteditable], .CodeMirror')) return;
  e.preventDefault();
  closeHelper();
});
$('helper-log').addEventListener('click', async (e) => {
  const start = e.target.closest('[data-start]');
  if (start) {
    const text = start.dataset.start;
    if (text.endsWith(' ')) { $('helper-input').value = text; $('helper-input').focus(); } // needs the rest typed
    else send(text);
    return;
  }
  const noteBtn = e.target.closest('[data-note]');
  if (noteBtn) {
    const log = load();
    const i = Number(noteBtn.dataset.note);
    const question = [...log.slice(0, i)].reverse().find((m) => m.role === 'user')?.text ?? 'Helper answer';
    openNoteMenu(noteBtn, { title: ctx.problem().title, heading: question.split('\n')[0].slice(0, 80), query: question, text: log[i].text, source: 'the Helper' });
    return;
  }
  const btn = e.target.closest('[data-insert], [data-copy], [data-replace], [data-replace-fn]');
  if (!btn) return;
  const code = btn.closest('.helper-code').querySelector('code').textContent;
  const label = btn.textContent;
  if (btn.hasAttribute('data-copy')) {
    await navigator.clipboard.writeText(code);
    btn.textContent = 'Copied';
  } else if (btn.hasAttribute('data-replace-fn')) {
    btn.textContent = ctx.replaceFunction(code) ? 'Replaced' : 'Not found in your code';
  } else if (btn.hasAttribute('data-replace')) {
    if (!confirm('Replace all the code in main.py with this?')) return;
    ctx.replace(code);
    btn.textContent = 'Replaced';
  } else {
    ctx.insert(code);
    btn.textContent = 'Inserted';
  }
  setTimeout(() => { btn.textContent = label; }, 1500);
});

/* Pictures */
const attached = []; // { media_type, data (base64), thumb (small data URL) }
const MAX_PICS = 4;

async function prepare(file) {
  const bmp = await createImageBitmap(file);
  const scale = Math.min(1, 1600 / Math.max(bmp.width, bmp.height));
  const draw = (s, type, q) => {
    const c = document.createElement('canvas');
    c.width = Math.round(bmp.width * s);
    c.height = Math.round(bmp.height * s);
    c.getContext('2d').drawImage(bmp, 0, 0, c.width, c.height);
    return c.toDataURL(type, q);
  };
  // Small PNG screenshots go as they are (sharp text); everything else becomes a 1600px JPEG.
  const keep = file.type === 'image/png' && file.size < 1_500_000 && scale === 1;
  const url = keep ? await new Promise((res) => { const r = new FileReader(); r.onload = () => res(r.result); r.readAsDataURL(file); })
    : draw(scale, 'image/jpeg', 0.9);
  const [head, data] = url.split(',');
  return { media_type: head.slice(5, head.indexOf(';')), data, thumb: draw(Math.min(1, 240 / Math.max(bmp.width, bmp.height)), 'image/jpeg', 0.75) };
}

async function addFiles(files) {
  for (const f of [...files].filter((f) => /^image\/(png|jpeg|gif|webp)$/.test(f.type))) {
    if (attached.length >= MAX_PICS) break;
    try { attached.push(await prepare(f)); } catch { /* not a readable picture */ }
  }
  renderAttach();
}

function renderAttach() {
  $('helper-attach').hidden = !attached.length;
  $('helper-attach').innerHTML = attached.map((p, i) => `<span class="attach-thumb"><img src="${p.thumb}" alt="Picture ${i + 1}">
    <button type="button" data-unattach="${i}" aria-label="Remove picture ${i + 1}">×</button></span>`).join('')
    + (attached.length ? `<span class="attach-count">${attached.length} of ${MAX_PICS}</span>` : '');
}

$('helper-pick').addEventListener('click', () => $('helper-file').click());
$('helper-file').addEventListener('change', (e) => { addFiles(e.target.files); e.target.value = ''; });
$('helper-attach').addEventListener('click', (e) => {
  const b = e.target.closest('[data-unattach]');
  if (b) { attached.splice(Number(b.dataset.unattach), 1); renderAttach(); }
});
$('helper-input').addEventListener('paste', (e) => {
  const files = [...(e.clipboardData?.files ?? [])].filter((f) => f.type.startsWith('image/'));
  if (files.length) { e.preventDefault(); addFiles(files); }
});
panel.addEventListener('dragover', (e) => { if ([...e.dataTransfer.types].includes('Files')) { e.preventDefault(); panel.classList.add('dropping'); } });
panel.addEventListener('dragleave', (e) => { if (!panel.contains(e.relatedTarget)) panel.classList.remove('dropping'); });
panel.addEventListener('drop', (e) => { e.preventDefault(); panel.classList.remove('dropping'); addFiles(e.dataTransfer.files); });
