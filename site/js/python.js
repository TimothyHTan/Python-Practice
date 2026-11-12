// The page's one Python engine (Pyodide in js/pyworker.js). It runs the student's code and also powers the
// editor's error checking and completions, so the page loads Python once instead of twice (~100 MB less).
// A program that runs too long gets a KeyboardInterrupt through a shared buffer; if it ignores that (or the
// page isn't cross-origin isolated, so there is no shared buffer), the worker is thrown away and restarted.
const GRACE_MS = 1500;
// [0] Pyodide's interrupt flag (2 = SIGINT), [1] "skip the remaining tests".
const stop = self.crossOriginIsolated ? new Int32Array(new SharedArrayBuffer(8)) : null;

export const status = { ready: false, tools: false, error: null };
const listeners = { ready: [], tools: [], error: [] };
const emit = (event, arg) => listeners[event].forEach((fn) => fn(arg));
export function on(event, fn) {
  listeners[event].push(fn);
  if (event === 'ready' && status.ready) fn();
  if (event === 'tools' && status.tools) fn();
}

let worker, nextId = 0;
const pending = new Map(); // id -> { resolve, reject, progress }

function boot() {
  Object.assign(status, { ready: false, tools: false, error: null });
  worker = new Worker('js/pyworker.js?v=6', { type: 'module' });
  worker.onmessage = ({ data }) => {
    if (data.type === 'ready') { status.ready = true; return emit('ready'); }
    if (data.type === 'tools-ready') { status.tools = true; return emit('tools'); }
    if (data.type === 'load-error') return fail(data.message);
    const job = pending.get(data.id);
    if (!job) return;
    if (data.type === 'progress') return job.progress?.(data);
    pending.delete(data.id);
    job.resolve(data.result);
  };
  worker.onerror = (e) => fail(e.message || 'Python failed to load. Check your internet connection.');
  worker.postMessage({ type: 'init', stop });
}
function fail(message) {
  status.error = message;
  for (const job of pending.values()) job.reject(new Error(message));
  pending.clear();
  emit('error', message);
}
function restart() {
  worker.terminate();
  for (const job of pending.values()) job.resolve(null);
  pending.clear();
  stop?.fill(0); // the new Python shares this buffer; a leftover stop would interrupt its startup
  boot();
}

function call(msg, progress) {
  if (status.error) return Promise.reject(new Error(status.error));
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, { resolve, reject, progress });
    worker.postMessage({ ...msg, id });
  });
}

// Editor tools: 'lint' { code }, 'complete' / 'signature' { code, line, col }. Null until they've loaded.
export const tool = (type, payload) => (status.tools ? call({ type, ...payload }).catch(() => null) : Promise.resolve(null));

// The likely mistake behind a failed run: { code, input, expected, got, error } or { code, timeout: true }
// -> { group, groupTitle, kind, title, detail, tip, line }, or null if it isn't available.
export const classify = (payload) => (status.ready ? call({ type: 'classify', payload }).catch(() => null) : Promise.resolve(null));

// Runs code once per input. Resolves with one { output, error } per input, or null if it hit the time limit.
// The clock starts after the libraries the code imports have downloaded.
export function run({ code, inputs, files = {}, testFiles = [] }, limitMs, onStatus) {
  if (stop) stop.fill(0);
  let timer, timedOut = false, settled = false;
  return call({ type: 'run', code, inputs, files, testFiles }, (d) => {
    if (d.text) return onStatus?.(d.text);
    timer = setTimeout(() => { // d.started
      timedOut = true;
      if (stop) { Atomics.store(stop, 1, 1); Atomics.store(stop, 0, 2); }
      setTimeout(() => { if (!settled) restart(); }, stop ? GRACE_MS : 0);
    }, limitMs);
  }).then((results) => {
    settled = true;
    clearTimeout(timer);
    return timedOut ? null : results;
  }, (e) => { settled = true; clearTimeout(timer); throw e; });
}

boot();
