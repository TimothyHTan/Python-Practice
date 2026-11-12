// Ctrl+K (or /) search over everything, on every page. Adds a Search button to the nav.
import { rank, noteDocs, queryTokens } from './search.js?v=5';
import { openNoteMenu } from './addnote.js?v=5';

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const KINDS = { all: 'All', fn: 'Functions', lesson: 'Lessons', problem: 'Problems', note: 'Notes' };
const EXAMPLES = ['letters to numbers', 'remove duplicates', 'read a csv file', 'days between dates', 'round to 2 decimals', 'sort a dict by value', 'skip broken lines', 'reverse a string'];

let baseDocs = null; // functions, lessons and problems: loaded on first open
let docs = [];
let results = [];
let active = 0;
let kind = 'all';

const dialog = document.createElement('dialog');
dialog.className = 'palette';
dialog.setAttribute('aria-label', 'Search');
dialog.innerHTML = `
  <div class="pal-head">
    <svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="m15.5 15.5 5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
    <input id="pal-q" type="search" autocomplete="off" spellcheck="false" placeholder="How do I… (e.g. convert letters to numbers)"
      role="combobox" aria-expanded="true" aria-controls="pal-list" aria-autocomplete="list">
    <button type="button" class="key pal-close" aria-label="Close search">Esc</button>
  </div>
  <div class="pal-filters" role="group" aria-label="Show">
    ${Object.entries(KINDS).map(([k, label]) => `<button type="button" class="key" data-kind="${k}" aria-pressed="${k === 'all'}">${label}</button>`).join('')}
  </div>
  <div class="pal-body">
    <ul id="pal-list" role="listbox" aria-label="Results"></ul>
    <div class="pal-preview" id="pal-preview"></div>
  </div>
  <p class="pal-foot"><span><kbd>↑</kbd><kbd>↓</kbd> move</span><span><kbd>Enter</kbd> open</span><span><kbd>Ctrl K</kbd> search from any page</span></p>`;
document.body.append(dialog);
const $q = dialog.querySelector('#pal-q');
const $list = dialog.querySelector('#pal-list');
const $preview = dialog.querySelector('#pal-preview');

const nav = document.querySelector('.nav');
if (nav) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'nav-search key';
  btn.innerHTML = '<svg aria-hidden="true" viewBox="0 0 24 24" width="16" height="16"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="m15.5 15.5 5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>Search<kbd>Ctrl K</kbd>';
  btn.addEventListener('click', () => openSearch());
  nav.append(btn);
}

async function loadBase() {
  const [{ recipes, categories, lessonDocs }, { problems, modules }] = await Promise.all([import('./learn-index.js?v=5'), import('./problems.js?v=5')]);
  const cat = Object.fromEntries(categories.map((c) => [c.id, c.title]));
  const mod = Object.fromEntries(modules.map((m) => [m.id, m.title]));
  return [
    ...recipes.map((r) => ({ kind: 'fn', title: r.title, where: `Function finder · ${cat[r.cat]}`, keys: r.keys, code: r.code,
      text: r.note, output: r.output, href: `learn.html#r-${r.id}` })),
    ...lessonDocs.map((d) => ({ kind: 'lesson', title: d.title, where: d.where, keys: '', code: d.code, text: d.text, href: `learn.html#${d.id}` })),
    ...problems.map((p) => ({ kind: 'problem', title: p.title, where: `Practice · ${mod[p.module]}${p.school ? ` · Pre-final ${p.school}` : ''}`,
      keys: (p.tips ?? []).join(' '), code: '', text: p.description.join(' '), href: `practice.html#${p.id}` })),
  ];
}

/* The nav Search key folds up in 3D and unfolds into the panel; closing folds it back into the key. */
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');
const navKey = () => document.querySelector('.nav-search');
let closing = null;

// Transform that shrinks the open panel onto the Search key, tipped back like a lid.
function onKey() {
  const key = navKey();
  if (!key?.offsetParent || reduceMotion.matches) return null;
  const k = key.getBoundingClientRect();
  const d = dialog.getBoundingClientRect();
  const dx = k.left + k.width / 2 - (d.left + d.width / 2);
  const dy = k.top + k.height / 2 - (d.top + d.height / 2);
  return `translate(${dx}px, ${dy}px) perspective(700px) rotateX(-75deg) scale(${k.width / d.width}, ${k.height / d.height})`;
}

function unfold() {
  const from = onKey();
  if (!from) { dialog.animate({ opacity: [0, 1] }, { duration: 150 }); return; }
  navKey().classList.add('lifted');
  dialog.animate({ opacity: [0, 1] }, { duration: 380, pseudoElement: '::backdrop' });
  dialog.animate([
    { transform: from, opacity: 0.3, borderRadius: '10px' },
    { offset: 0.62, transform: 'perspective(700px) rotateX(7deg) scale(1.02)', opacity: 1 },
    { transform: 'perspective(700px) rotateX(0deg) scale(1)', opacity: 1 },
  ], { duration: 600, easing: 'cubic-bezier(.2, .75, .25, 1)' });
  [...dialog.children].forEach((el, i) =>
    el.animate({ opacity: [0, 1], transform: ['translateY(8px)', 'none'] }, { duration: 260, delay: 230 + i * 45, easing: 'ease-out', fill: 'backwards' }));
}

export function closeSearch() {
  if (!dialog.open) return Promise.resolve();
  closing ??= (async () => {
    const to = onKey();
    const anims = [];
    if (to) {
      for (const el of dialog.children) anims.push(el.animate({ opacity: [1, 0] }, { duration: 110, fill: 'forwards' }));
      anims.push(dialog.animate({ opacity: [1, 0] }, { duration: 380, pseudoElement: '::backdrop', fill: 'forwards' }));
      const fold = dialog.animate([
        { transform: 'perspective(700px) rotateX(0deg) scale(1)', opacity: 1 },
        { offset: 0.28, transform: 'perspective(700px) rotateX(6deg) scale(1.015)', opacity: 1 },
        { transform: to, opacity: 0.25, borderRadius: '10px' },
      ], { duration: 430, easing: 'cubic-bezier(.55, 0, .7, .2)', fill: 'forwards' });
      anims.push(fold);
      await fold.finished;
    }
    dialog.close();
    anims.forEach((a) => a.cancel());
    const key = navKey();
    if (key?.classList.contains('lifted')) {
      key.classList.remove('lifted');
      key.animate({ transform: ['translateY(3px) scale(.94)', 'none'] }, { duration: 260, easing: 'cubic-bezier(.3, 1.6, .5, 1)' });
    }
    closing = null;
  })();
  return closing;
}

export async function openSearch(query) {
  if (!dialog.open) { dialog.showModal(); unfold(); }
  if (query != null) $q.value = query;
  $q.focus();
  $q.select();
  if (!baseDocs) {
    $list.innerHTML = '<li class="pal-empty">Loading…</li>';
    baseDocs = await loadBase();
  }
  // Notes change on the notes page, so read them fresh every time.
  docs = [...baseDocs, ...noteDocs(JSON.parse(localStorage.getItem('vw.notes') ?? '[]'))];
  update();
}

function marker(words) {
  const parts = words.filter((w) => w.length > 1).map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  if (!parts.length) return esc;
  const re = new RegExp(`\\b(${parts.join('|')})`, 'gi');
  return (s) => esc(s).replace(re, '<mark>$1</mark>');
}

function update() {
  const q = $q.value.trim();
  if (!q) {
    results = [];
    $list.innerHTML = `<li class="pal-empty">Type what you want to do in plain words.<div class="pal-examples">${
      EXAMPLES.map((e) => `<button type="button" class="key" data-q="${esc(e)}">${esc(e)}</button>`).join('')}</div></li>`;
    $preview.innerHTML = '';
    $q.removeAttribute('aria-activedescendant');
    return;
  }
  results = rank(q, kind === 'all' ? docs : docs.filter((d) => d.kind === kind), 30);
  active = 0;
  const mark = marker(queryTokens(q));
  $list.innerHTML = results.length
    ? results.map((d, i) => `<li role="option" id="pal-o${i}" aria-selected="${i === 0}" data-i="${i}">
        <a href="${esc(d.href)}" tabindex="-1"><span class="kind kind-${d.kind}">${KINDS[d.kind].replace(/s$/, '')}</span>
        <span class="t">${mark(d.title)}</span><span class="w">${esc(d.where)}</span></a></li>`).join('')
    : `<li class="pal-empty">Nothing found for “${esc(q)}”. Try fewer or simpler words, like <b>split</b> or <b>sort list</b>.</li>`;
  show(0);
}

function show(i) {
  if (!results.length) { $preview.innerHTML = ''; return; }
  active = (i + results.length) % results.length;
  $list.querySelectorAll('[role=option]').forEach((li) => li.setAttribute('aria-selected', String(Number(li.dataset.i) === active)));
  const li = $list.querySelector(`#pal-o${active}`);
  li?.scrollIntoView({ block: 'nearest' });
  $q.setAttribute('aria-activedescendant', `pal-o${active}`);
  const d = results[active];
  const mark = marker(queryTokens($q.value));
  const open = { fn: 'Open in the Function finder', lesson: 'Open the lesson', problem: 'Open the problem', note: 'Open the note' }[d.kind];
  $preview.innerHTML = `
    <p class="w">${esc(d.where)}</p>
    <h3>${mark(d.title)}</h3>
    ${d.code ? `<pre class="cm-s-vw code-view"><code>${highlight(d.code)}</code></pre>` : ''}
    ${d.output ? `<p class="out-label">Output</p><pre class="out">${esc(d.output)}</pre>` : ''}
    ${d.text && d.kind === 'note' ? `<div class="txt md" id="pal-md">${mark(d.text.slice(0, 700))}</div>` : ''}
    ${d.text && d.kind !== 'fn' && d.kind !== 'note' ? `<p class="txt">${mark(d.text.slice(0, 420))}${d.text.length > 420 ? '…' : ''}</p>` : ''}
    ${d.text && d.kind === 'fn' ? `<p class="txt">${esc(d.text)}</p>` : ''}
    <div class="pal-actions">
      ${d.code ? '<button type="button" class="key" data-copy>Copy code</button>' : ''}
      ${d.kind === 'fn' || d.kind === 'lesson' ? '<button type="button" class="key" data-addnote>Add to notes</button>' : ''}
      <a class="key go" href="${esc(d.href)}">${open}</a>
    </div>`;
  if (d.kind === 'note') showNote(d);
}

// Notes are markdown: show them formatted (minus the heading already shown as the title), once the renderer loads.
async function showNote(d) {
  const { renderMarkdown } = await import('./markdown.js?v=5').catch(() => ({}));
  const box = $preview.querySelector('#pal-md');
  if (!renderMarkdown || !box || results[active] !== d) return;
  const body = d.text.replace(/^#{1,6}\s+.*\n?/, '');
  box.innerHTML = renderMarkdown(body.length > 1200 ? body.slice(0, 1200) + '\n\n…' : body);
}

export function highlight(code) {
  const CM = window.CodeMirror;
  if (!CM?.runMode) return esc(code);
  const out = [];
  CM.runMode(code, 'python', (text, style) => out.push(style ? `<span class="cm-${style.replace(/ +/g, ' cm-')}">${esc(text)}</span>` : esc(text)));
  return out.join('');
}

async function go(i = active) {
  const d = results[i];
  if (!d) return;
  await closeSearch();
  location.href = d.href; // same-page hash links fire hashchange; other pages load
}

$q.addEventListener('input', update);
$q.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); show(active + (e.key === 'ArrowDown' ? 1 : -1)); }
  else if (e.key === 'Enter') { e.preventDefault(); go(); }
  else if (e.key === 'Escape') { e.preventDefault(); closeSearch(); } // a search box would only clear itself
});
$list.addEventListener('mousemove', (e) => {
  const li = e.target.closest('[role=option]');
  if (li && Number(li.dataset.i) !== active) show(Number(li.dataset.i));
});
$list.addEventListener('click', (e) => {
  const ex = e.target.closest('[data-q]');
  if (ex) { $q.value = ex.dataset.q; update(); $q.focus(); return; }
  const li = e.target.closest('[role=option]');
  if (li && !e.ctrlKey && !e.metaKey) { e.preventDefault(); go(Number(li.dataset.i)); }
});
dialog.querySelector('.pal-filters').addEventListener('click', (e) => {
  const b = e.target.closest('[data-kind]');
  if (!b) return;
  kind = b.dataset.kind;
  dialog.querySelectorAll('[data-kind]').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
  update();
  $q.focus();
});
$preview.addEventListener('click', (e) => {
  const b = e.target.closest('[data-addnote]');
  if (!b) return;
  const d = results[active];
  const topic = d.where.split(' · ').pop();
  openNoteMenu(b, {
    title: topic, heading: d.title, query: `${d.title} ${d.keys ?? ''}`, source: d.kind === 'fn' ? 'the Function finder' : 'the Learn page',
    text: [d.code && '```python\n' + d.code + '\n```', d.output && 'Output:\n```\n' + d.output + '\n```', d.text && d.text.slice(0, 600)].filter(Boolean).join('\n'),
  });
});
$preview.addEventListener('click', async (e) => {
  const b = e.target.closest('[data-copy]');
  if (!b) return;
  await navigator.clipboard.writeText(results[active].code);
  b.textContent = 'Copied';
  setTimeout(() => { b.textContent = 'Copy code'; }, 1500);
});
$preview.addEventListener('click', (e) => {
  if (!e.target.closest('a') || e.ctrlKey || e.metaKey) return;
  e.preventDefault();
  go();
});
dialog.querySelector('.pal-close').addEventListener('click', () => closeSearch());
dialog.addEventListener('cancel', (e) => { e.preventDefault(); closeSearch(); }); // Esc outside the search box
dialog.addEventListener('click', (e) => { if (e.target === dialog) closeSearch(); }); // click on the backdrop

const typing = (el) => el.closest?.('input, textarea, select, [contenteditable], .CodeMirror');
// Capture phase so Ctrl+K works even inside the code editor (its own Ctrl+K chords are rarely used).
addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && e.key.toLowerCase() === 'k') {
    e.preventDefault();
    e.stopPropagation();
    dialog.open ? closeSearch() : openSearch();
  } else if (e.key === '/' && !e.ctrlKey && !e.metaKey && !dialog.open && !typing(e.target)) {
    e.preventDefault();
    openSearch();
  }
}, true);
