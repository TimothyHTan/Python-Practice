// The page's one Pyodide (driven by js/python.js): runs student code off the main thread, and runs the editor's
// language tools (js/pylang.py: error checking, completions, call hints) between runs.
// Module worker: this Pyodide version refuses to load in a classic (importScripts) worker.
import { loadPyodide } from 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs';

const MAX_CHARS = 100_000;
let out = '';
const decoder = new TextDecoder();
const write = (buf) => { if (out.length < MAX_CHARS) out += decoder.decode(buf, { stream: true }); return buf.length; };

let stop = null; // shared with the page: [0] interrupt flag, [1] skip the remaining tests
let ready, tools, classifier;

function start() {
  ready = loadPyodide().then((py) => {
    py.setStdout({ write });
    py.setStderr({ write });
    if (stop) py.setInterruptBuffer(stop);
    py.runPython(`
import io, os, sys
_home, _limit = os.getcwd(), sys.getrecursionlimit()

def _feed(text):
    # A fresh stdin per run: the shared buffered one kept unread lines and fed them to the next run.
    sys.stdin = io.StringIO(text + '\\n' if text else '')

def _warm_imports(code):
    import importlib
    from pyodide.code import find_imports
    for name in find_imports(code):
        try:
            importlib.import_module(name)
        except BaseException:
            pass  # the student's own import line will show the real error

def _reset():
    # Undo what one program could do to the next one, or to the editor tools sharing this Python.
    sys.stdout.flush(); sys.stderr.flush()
    sys.stdout, sys.stderr, sys.stdin = sys.__stdout__, sys.__stderr__, sys.__stdin__
    sys.setrecursionlimit(_limit)
    os.chdir(_home)
`);
    postMessage({ type: 'ready' });
    return py;
  });
  // Language tools load after Python is ready, so a first Run never waits for them.
  tools = ready.then(async (py) => {
    await py.loadPackage(['jedi', 'micropip']);
    // pyflakes is not bundled with Pyodide; if PyPI is unreachable we still get syntax errors.
    await py.pyimport('micropip').install('pyflakes').catch(() => {});
    py.runPython(await (await fetch(new URL('pylang.py', import.meta.url))).text());
    postMessage({ type: 'tools-ready' });
    return Object.fromEntries(['lint', 'complete', 'signature'].map((n) => [n, py.globals.get(n)]));
  });
  // ../mistakes.py names the kind of mistake behind a failed run (also used by notes_store.py for Progress).
  classifier = ready.then(async (py) => {
    const ns = py.globals.get('dict')();
    ns.set('__name__', 'mistakes'); // not __main__, so its self-check doesn't run here
    py.runPython(await (await fetch(new URL('../mistakes.py', import.meta.url))).text(), { globals: ns });
    return ns.get('classify_json');
  });
  ready.catch((e) => postMessage({ type: 'load-error', message: String(e) }));
  classifier.catch(() => {}); // results still show without it
  tools.catch(() => {}); // the editor keeps working without them
}

async function runCode(py, { id, code, inputs, files, testFiles }) {
  // Download libraries the code imports (numpy, pandas, ...) and import them once,
  // so that slow first-time loading does not count against the time limit.
  await py.loadPackagesFromImports(code, {
    messageCallback: (text) => postMessage({ type: 'progress', id, text }),
  }).catch(() => {});
  py.globals.get('_warm_imports')(code);
  postMessage({ type: 'progress', id, started: true });
  const results = [];
  for (const [i, input] of inputs.entries()) {
    if (stop && Atomics.load(stop, 1)) break; // timed out: the page stops waiting anyway
    out = '';
    // Fresh copies of the problem's data files every run, in case the last run changed them.
    // Some hidden tests swap in a different version of a data file.
    for (const [name, content] of Object.entries({ ...files, ...testFiles[i] })) py.FS.writeFile(name, content);
    py.globals.get('_feed')(input);
    const globals = py.globals.get('dict')();
    let error = null;
    try {
      py.runPython(code, { globals });
    } catch (e) {
      // Keep the Python traceback lines from the student's code, drop Pyodide internals.
      const lines = String(e.message).split('\n');
      const start = lines.findIndex((l) => l.includes('File "<exec>"'));
      error = (start > -1 ? lines.slice(start) : lines.slice(-3)).join('\n').trim();
    } finally {
      py.globals.get('_reset')();
      globals.destroy();
    }
    if (out.length >= MAX_CHARS) out = out.slice(0, MAX_CHARS) + '\n... output cut off here';
    results.push({ output: out, error });
  }
  if (stop) Atomics.store(stop, 0, 0); // a stop that landed after the program ended must not hit the next job
  return results;
}

async function handle(data) {
  if (data.type === 'run') return runCode(await ready, data);
  if (data.type === 'classify') return JSON.parse((await classifier)(JSON.stringify(data.payload)));
  const fns = await tools;
  const py = await ready;
  if (data.type === 'lint') {
    // Fetch libraries the code imports (numpy etc.) so completions know them too.
    await py.loadPackagesFromImports(data.code).catch(() => {});
    return JSON.parse(fns.lint(data.code));
  }
  return JSON.parse(fns[data.type](data.code, data.line, data.col));
}

// One job at a time, in order: Python can't run two things at once anyway.
let queue = Promise.resolve();
self.onmessage = ({ data }) => {
  if (data.type === 'init') { stop = data.stop; return start(); }
  queue = queue.then(() => handle(data).catch(() => null)).then((result) => postMessage({ type: 'result', id: data.id, result }));
};
