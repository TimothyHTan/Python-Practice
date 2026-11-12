// Mirrors progress to Documents\python notes through the local server (server.py -> notes_store.py).
// localStorage stays the fast working copy; this sends changes and restores anything the browser lost.
import { problems } from './problems.js?v=5';

const starter = Object.fromEntries(problems.map((p) => [p.id, p.starter]));
const local = (k) => JSON.parse(localStorage.getItem('vw.' + k) ?? 'null');
const pending = { code: {}, pseudo: {}, attempts: [] };
let timer = null;
const listeners = new Set();
export let state = { ok: null, folder: '', savedAt: null, analytics: null, error: '' };

export const onSync = (fn) => { listeners.add(fn); if (state.ok !== null) fn(state); };

// Visits used to auto-save the starter line; it isn't the student's work, so it's sent as empty.
const realCode = (id, text) => (text === starter[id] ? '' : text ?? '');

function small() {
  const solvedAt = local('solvedAt') ?? Object.fromEntries((local('solved') ?? []).map((id) => [id, 0]));
  return { solvedAt, lessonsDone: local('lessons.done') ?? [] };
}

async function post(body, keepalive = false) {
  const res = await fetch('/api/sync', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), keepalive,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error ?? `Saving failed (${res.status})`);
  return data;
}

function report(data, error) {
  state = error
    ? { ...state, ok: false, error: error.message.includes('fetch') ? 'The local server is not running, so this was saved in the browser only.' : error.message }
    : { ok: true, folder: data.folder, savedAt: new Date(), analytics: data.analytics, error: '' };
  listeners.forEach((fn) => fn(state));
}

export async function flush(keepalive = false) {
  clearTimeout(timer);
  const sent = { code: pending.code, pseudo: pending.pseudo, attempts: pending.attempts };
  pending.code = {}; pending.pseudo = {}; pending.attempts = [];
  try {
    report(await post({ ...sent, ...small() }, keepalive));
  } catch (e) {
    // Put it back so the next save retries it; newer edits win.
    pending.code = { ...sent.code, ...pending.code };
    pending.pseudo = { ...sent.pseudo, ...pending.pseudo };
    pending.attempts = [...sent.attempts, ...pending.attempts];
    report(null, e);
  }
}

const soon = (ms = 1500) => { clearTimeout(timer); timer = setTimeout(flush, ms); };
export const saveCode = (id, text) => { pending.code[id] = realCode(id, text); soon(); };
export const savePseudo = (id, text) => { pending.pseudo[id] = text; soon(); };
export const logAttempt = (a) => { pending.attempts.push({ ...a, t: Date.now() }); soon(300); };
export const saveSoon = () => soon();

// Send everything; restore what this browser is missing. Reloads once if it restored anything.
async function syncAll() {
  const code = {}, pseudo = {};
  for (let i = 0; i < localStorage.length; i++) {
    const m = /^vw\.(code|pseudo)\.([a-z0-9-]+)$/.exec(localStorage.key(i));
    if (!m) continue;
    const text = local(`${m[1]}.${m[2]}`) ?? '';
    if (m[1] === 'code') code[m[2]] = realCode(m[2], text); else pseudo[m[2]] = text;
  }
  try {
    const data = await post({ code, pseudo, ...small(), attempts: pending.attempts.splice(0), full: true });
    let restored = 0;
    for (const [kind, items] of [['code', data.code], ['pseudo', data.pseudo]]) {
      for (const [id, text] of Object.entries(items ?? {})) { localStorage.setItem(`vw.${kind}.${id}`, JSON.stringify(text)); restored++; }
    }
    const before = JSON.stringify(small());
    localStorage.setItem('vw.solvedAt', JSON.stringify(data.solvedAt));
    localStorage.setItem('vw.lessons.done', JSON.stringify(data.lessonsDone));
    if (restored || JSON.stringify(small()) !== before) {
      if (!sessionStorage.getItem('vw.restored')) { sessionStorage.setItem('vw.restored', '1'); location.reload(); return; }
    }
    sessionStorage.removeItem('vw.restored');
    report(data);
  } catch (e) { report(null, e); }
}

addEventListener('pagehide', () => {
  if (Object.keys(pending.code).length || Object.keys(pending.pseudo).length || pending.attempts.length) flush(true);
});

syncAll();
