// "Add to notes": a small menu that suggests the note that fits best (by title, then by search) and
// appends the text to the bottom of it as a new "## heading" section. Notes live in localStorage (vw.notes).
import { rank } from './search.js?v=5';

const KEY = 'vw.notes';
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const load = () => JSON.parse(localStorage.getItem(KEY) ?? '[]');

// Best existing notes for this content: an exact title match first, then search over titles and text.
export function suggestNotes(title, query, limit = 3) {
  const notes = load();
  const exact = notes.filter((n) => n.title.trim().toLowerCase() === title.trim().toLowerCase());
  const docs = notes.map((n) => ({ kind: 'note', note: n, title: n.title, keys: '', where: '', code: '', text: n.body.slice(0, 4000) }));
  const found = rank(`${title} ${query}`, docs, 10).map((d) => d.note);
  return [...new Set([...exact, ...found])].slice(0, limit);
}

// Appends a section to the note with this id (or makes a new note with `title`). Returns the note and where it starts.
export function appendToNote(id, title, heading, text, source) {
  const notes = load();
  let note = notes.find((n) => n.id === id);
  if (!note) {
    note = { id: crypto.randomUUID(), title, body: '', updated: Date.now() };
    notes.push(note);
  }
  const stamp = new Date().toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
  const before = note.body.replace(/\s+$/, '');
  const at = before ? before.length + 2 : 0;
  note.body = `${before ? before + '\n\n' : ''}## ${heading}\n${text.trim()}\n(added ${stamp} from ${source})\n`;
  note.updated = Date.now();
  localStorage.setItem(KEY, JSON.stringify(notes));
  return { note, at };
}

let menu = null;
function closeMenu() {
  menu?.remove();
  menu = null;
  removeEventListener('pointerdown', outside, true);
  removeEventListener('keydown', onKey, true);
}
const outside = (e) => { if (menu && !menu.contains(e.target)) closeMenu(); };
const onKey = (e) => { if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeMenu(); } };

// opts: { title: suggested note title, heading: section heading, text, source, query? }
export function openNoteMenu(anchor, opts) {
  closeMenu();
  const picks = suggestNotes(opts.title, opts.query ?? opts.heading);
  const hasExact = picks.some((n) => n.title.trim().toLowerCase() === opts.title.trim().toLowerCase());
  menu = document.createElement('div');
  menu.className = 'note-menu';
  menu.setAttribute('role', 'menu');
  menu.innerHTML = `<p class="note-menu-title">Add to a note</p>
    ${picks.map((n, i) => `<button type="button" role="menuitem" data-id="${esc(n.id)}">${i === 0 ? '<span class="best">Best match</span>' : ''}${esc(n.title || 'Untitled note')}</button>`).join('')}
    ${hasExact ? '' : `<button type="button" role="menuitem" data-new>New note “${esc(opts.title)}”</button>`}`;
  // Inside a modal <dialog> (the search panel) the rest of the page can't be clicked, so open in it.
  const host = anchor.closest('dialog') ?? document.body;
  host.append(menu);
  const base = host === document.body ? { left: 0, top: 0 } : host.getBoundingClientRect();
  const r = anchor.getBoundingClientRect();
  const h = menu.offsetHeight, w = menu.offsetWidth;
  menu.style.left = `${Math.min(Math.max(8, r.left), innerWidth - w - 8) - base.left}px`;
  menu.style.top = `${(r.bottom + h + 8 < innerHeight ? r.bottom + 6 : r.top - h - 6) - base.top}px`;
  menu.querySelector('button')?.focus();
  menu.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    const { note, at } = appendToNote(b.dataset.id ?? null, opts.title, opts.heading, opts.text, opts.source);
    menu.innerHTML = `<p class="note-menu-done">Added to “${esc(note.title)}”.</p>
      <a class="key go" href="notes.html#note=${encodeURIComponent(note.id)}&at=${at}">Open the note</a>`;
    setTimeout(closeMenu, 4000);
  });
  addEventListener('pointerdown', outside, true);
  addEventListener('keydown', onKey, true);
}
