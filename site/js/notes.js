const KEY = 'vw.notes';
const $ = (id) => document.getElementById(id);
const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

let notes = JSON.parse(localStorage.getItem(KEY) ?? '[]');
// Reading view: the note as formatted markdown. Click any part of it (or Edit, or Ctrl+E) to edit the text there.
// Until js/markdown.js has loaded (or if it can't), the note simply stays in the editor.
let md = null;
let editing = false;
import('./markdown.js?v=5').then((m) => { md = m; render(); openFromHash(); }).catch(() => {});
let currentId = notes[0]?.id ?? null;
const save = () => localStorage.setItem(KEY, JSON.stringify(notes));
const current = () => notes.find((n) => n.id === currentId);

const words = () => $('note-q').value.toLowerCase().split(/\s+/).filter(Boolean);
const matches = (n, ws) => ws.every((w) => `${n.title}\n${n.body}`.toLowerCase().includes(w));
const reEscape = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const markWords = (text, ws) => esc(text).replace(new RegExp(`(${ws.map((w) => reEscape(esc(w))).join('|')})`, 'gi'), '<mark>$1</mark>');

// The line of the body where the first search word appears, for the list preview.
function hitLine(note, ws) {
  const at = note.body.toLowerCase().indexOf(ws[0]);
  if (at < 0) return '';
  const start = note.body.lastIndexOf('\n', at) + 1;
  const end = note.body.indexOf('\n', at);
  const line = note.body.slice(Math.max(start, at - 60), end < 0 ? undefined : Math.min(end, at + 80)).trim();
  return `<span class="note-hit">${markWords(line, ws)}</span>`;
}

function render() {
  const ws = words();
  const all = [...notes].sort((a, b) => b.updated - a.updated);
  const list = ws.length ? all.filter((n) => matches(n, ws)) : all;
  $('note-count').textContent = ws.length ? `${list.length} of ${notes.length} notes match` : '';
  $('list').innerHTML = list.map((n) => `
    <li><button class="note" data-id="${n.id}" aria-current="${n.id === currentId}">
      <span class="note-title">${ws.length ? markWords(n.title || 'Untitled note', ws) : esc(n.title || 'Untitled note')}</span>
      <span class="when">${new Date(n.updated).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</span>
      ${ws.length ? hitLine(n, ws) : ''}
    </button></li>`).join('');

  const note = current();
  $('empty').hidden = !!note;
  for (const id of ['title', 'note-actions']) $(id).hidden = !note;
  const reading = !!note && !!md && !editing && note.body.trim() !== '';
  $('body').hidden = !note || reading;
  $('view').hidden = !reading;
  $('mode').hidden = !md || !note;
  $('mode').textContent = reading ? 'Edit' : 'Done';
  $('mode').title = reading ? 'Edit the text (Ctrl+E)' : 'Show it formatted (Ctrl+E or Esc)';
  if (note) {
    $('title').value = note.title;
    $('body').value = note.body;
    if (reading) $('view').innerHTML = md.markdownBlocks(note.body).map((b) => `<div class="md-block" data-at="${b.at}">${b.html}</div>`).join('');
  }
}

// Switch between the formatted note and the editor, keeping the same spot on screen.
function setEditing(on, at = null) {
  editing = on;
  render();
  if (on) reveal(at ?? $('body').value.length, 0);
}

// In the reading view: scroll to the block holding text offset `at`, and flash it.
function showInView(at) {
  const blocks = [...$('view').querySelectorAll('.md-block')];
  const block = blocks.filter((b) => Number(b.dataset.at) <= at).pop() ?? blocks[0];
  if (!block) return;
  block.scrollIntoView({ block: 'center' });
  block.classList.remove('flash');
  void block.offsetWidth; // restart the animation
  block.classList.add('flash');
}
const reading = () => !$('view').hidden;

// Select text in the note body and scroll it into view (measured with a hidden copy of the textarea).
function reveal(at, length) {
  const ta = $('body');
  ta.focus({ preventScroll: true });
  ta.setSelectionRange(at, at + length);
  const style = getComputedStyle(ta);
  const mirror = document.createElement('div');
  for (const k of ['font', 'padding', 'border', 'boxSizing', 'letterSpacing', 'tabSize']) mirror.style[k] = style[k];
  Object.assign(mirror.style, { position: 'absolute', visibility: 'hidden', whiteSpace: 'pre-wrap', overflowWrap: 'break-word', width: `${ta.clientWidth}px` });
  mirror.textContent = ta.value.slice(0, at);
  document.body.append(mirror);
  ta.scrollTop = Math.max(0, mirror.offsetHeight - ta.clientHeight / 3);
  mirror.remove();
}

function openFromHash() {
  const params = new URLSearchParams(location.hash.slice(1));
  const note = notes.find((n) => n.id === params.get('note'));
  if (!note) return;
  currentId = note.id;
  $('note-q').value = '';
  render();
  editing = false;
  render();
  const at = Math.min(Number(params.get('at')) || 0, note.body.length);
  if (reading()) return showInView(at);
  const lineEnd = note.body.indexOf('\n', at);
  reveal(at, (lineEnd < 0 ? note.body.length : lineEnd) - at);
}

function create() {
  const note = { id: crypto.randomUUID(), title: '', body: '', updated: Date.now() };
  notes.push(note);
  currentId = note.id;
  editing = true;
  save();
  render();
  $('title').focus();
}

function edit() {
  const note = current();
  note.title = $('title').value;
  note.body = $('body').value;
  note.updated = Date.now();
  save();
  $('saved').textContent = 'Saved';
  // Update only the list so typing doesn't lose focus.
  const btn = $('list').querySelector(`[data-id="${note.id}"] .note-title`);
  if (btn) btn.textContent = note.title || 'Untitled note';
}

$('new').addEventListener('click', create);
$('new-empty').addEventListener('click', create);
$('title').addEventListener('input', edit);
$('body').addEventListener('input', edit);
$('mode').addEventListener('click', () => setEditing(!editing && reading()));
$('view').addEventListener('click', (e) => {
  if (e.target.closest('a') || !getSelection().isCollapsed) return; // links still work; selecting text doesn't edit
  const block = e.target.closest('.md-block');
  setEditing(true, block ? Number(block.dataset.at) : null);
});
addEventListener('keydown', (e) => {
  if (!current() || !md) return;
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'e') { e.preventDefault(); setEditing(reading()); }
  else if (e.key === 'Escape' && e.target === $('body')) setEditing(false);
});
$('body').addEventListener('keydown', (e) => {
  if (e.key !== 'Tab') return; // let Tab indent code snippets
  e.preventDefault();
  e.target.setRangeText('    ', e.target.selectionStart, e.target.selectionEnd, 'end');
  edit();
});
$('list').addEventListener('click', (e) => {
  const id = e.target.closest('button')?.dataset.id;
  if (!id) return;
  currentId = id;
  editing = false;
  $('saved').textContent = '';
  render();
  const ws = words();
  const at = ws.length ? current().body.toLowerCase().indexOf(ws[0]) : -1;
  if (at >= 0) reading() ? showInView(at) : reveal(at, ws[0].length); // jump to the first match
});
$('note-q').addEventListener('input', render);
$('note-q').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') $('list').querySelector('button.note')?.click();
  if (e.key === 'Escape' && e.target.value) { e.target.value = ''; render(); }
});
addEventListener('hashchange', openFromHash);
$('delete').addEventListener('click', () => {
  const note = current();
  if (!confirm(`Delete "${note.title || 'Untitled note'}"? This can't be undone.`)) return;
  notes = notes.filter((n) => n.id !== note.id);
  currentId = notes[0]?.id ?? null;
  save();
  render();
});

// First visit only: add the pre-final notes as a note. Deleting it later keeps it deleted.
async function seedPrefinalNotes() {
  if (localStorage.getItem('vw.seeded.prefinal')) return;
  try {
    const res = await fetch('assets/python_practice_notes.md');
    if (!res.ok) return;
    const body = await res.text();
    notes.push({ id: crypto.randomUUID(), title: 'Pre-final: problems, misses and solutions', body, updated: Date.now() });
    currentId ??= notes.at(-1).id;
    save();
    localStorage.setItem('vw.seeded.prefinal', '1');
  } catch { /* offline or file missing: try again next visit */ }
}

seedPrefinalNotes().then(() => { render(); openFromHash(); });
addEventListener('storage', (e) => {
  if (e.key !== KEY) return;
  notes = JSON.parse(e.newValue ?? '[]');
  if (!current()) currentId = notes[0]?.id ?? null;
  render();
});
