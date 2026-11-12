import { problems, modules, files, plan } from './problems.js?v=5';
import { isSolved, markSolved, doneOnDay, dayItems, todayIndex, difficulty, difficultyLabel } from './progress.js?v=5';
import { sameOutput } from './grade.js?v=5';
import { flash } from './badge.js?v=5';
import { createEditor } from './editor.js?v=6';
import * as python from './python.js?v=6';
import { makeSplitter } from './split.js?v=5';
import { saveCode, savePseudo, logAttempt } from './sync.js?v=5';
import { initHelper } from './helper.js?v=5';
import { findFunction, functionName, replaceFunction } from './pyblocks.js?v=5';
import { problemLevel, levelTitle } from './problem-levels.js?v=5';

const $ = (id) => document.getElementById(id);
const store = {
  get: (k, fallback) => JSON.parse(localStorage.getItem('vw.' + k) ?? 'null') ?? fallback,
  set: (k, v) => localStorage.setItem('vw.' + k, JSON.stringify(v)),
};
const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const inline = (s) => esc(s).replace(/`([^`]+)`/g, '<code>$1</code>');
const show = (s) => (s === '' ? '(nothing)' : s);

// The hash picks the problem; without one (the nav's Practice link) reopen the last problem you were on.
const byId = (id) => problems.find((p) => p.id === id);
let current = byId(location.hash.slice(1)) ?? byId(store.get('last')) ?? problems[0];
const moduleOf = (p) => modules.find((m) => m.id === p.module);

// Opened from the plan page (?day=N): show that day's progress and a "next" button.
const planDay = (() => {
  const n = Number(new URLSearchParams(location.search).get('day'));
  return plan.days[n - 1] ? n - 1 : null;
})();
const filesOf = (p) => Object.fromEntries((p.files ?? []).map((name) => [name, files[name]]));

/* Editor */
const editor = createEditor($('code'), () => submit(true), showProblemCount);
editor.on('cursorActivity', () => {
  const { line, ch } = editor.getCursor();
  $('cursor-pos').textContent = `Ln ${line + 1}, Col ${ch + 1}`;
});
function showProblemCount(found) {
  const errors = found.filter((f) => f.severity === 'error').length;
  const warnings = found.length - errors;
  $('problems-count').innerHTML = !found.length
    ? '<span class="count ok">No problems</span>'
    : [errors && `<span class="count err">${errors} error${errors > 1 ? 's' : ''}</span>`,
       warnings && `<span class="count warn">${warnings} warning${warnings > 1 ? 's' : ''}</span>`]
      .filter(Boolean).join(' ');
}
editor.on('change', () => { store.set('code.' + current.id, editor.getValue()); saveCode(current.id, editor.getValue()); markErrorLine(null); });
$('pseudo').addEventListener('input', (e) => { store.set('pseudo.' + current.id, e.target.value); savePseudo(current.id, e.target.value); });

// Highlight the line a run-time error points at, until the code changes.
let errorLine = null;
function markErrorLine(error, line = null) {
  if (errorLine) editor.removeLineClass(errorLine, 'background', 'err-line');
  const n = line ?? [...(error ?? '').matchAll(/File "<exec>", line (\d+)/g)].pop()?.[1];
  errorLine = n && n <= editor.lineCount() ? editor.addLineClass(n - 1, 'background', 'err-line') : null;
}

/* Tabs: two independent tab lists (editor on top, output panel below) */
function openTab(id) {
  for (const t of $(id).closest('[role=tablist]').querySelectorAll('[role=tab]')) {
    const on = t.id === id;
    t.setAttribute('aria-selected', on);
    $(t.getAttribute('aria-controls')).hidden = !on;
  }
  if (id === 'e-code') editor.refresh();
}
document.querySelectorAll('[role=tab]').forEach((t) => t.addEventListener('click', () => openTab(t.id)));

/* Resizable panels */
makeSplitter($('splitter-x'), {
  container: $('split-x'), cssVar: '--problem-w', axis: 'x',
  min: 20, max: 70, initial: 42, storageKey: 'vw.split.x', onResize: () => editor.refresh(),
});
makeSplitter($('splitter-y'), {
  container: $('split-y'), cssVar: '--editor-h', axis: 'y',
  min: 20, max: 85, initial: 62, storageKey: 'vw.split.y', onResize: () => editor.refresh(),
});

/* Sidebar: problems grouped by module */
const openModules = new Set();
function renderList() {
  openModules.add(current.module);
  const t = todayIndex();
  const today = plan.days[Math.max(0, Math.min(t, plan.days.length - 1))];
  const dayNo = plan.days.indexOf(today) + 1;
  $('plan-link').innerHTML = `<a href="plan.html">${t < 0 ? 'Plan starts ' + (t === -1 ? 'tomorrow' : 'soon') : t >= plan.days.length ? 'Plan finished' : 'Today'}<strong>Day ${dayNo}: ${esc(today.title)}</strong></a>`;
  $('problem-list').innerHTML = modules.map((m) => {
    const list = problems.filter((p) => p.module === m.id);
    const done = list.filter((p) => isSolved(p.id)).length;
    return `<li><details data-module="${m.id}" ${openModules.has(m.id) ? 'open' : ''}>
      <summary><span>${esc(m.title)}</span><span class="progress-count">${done}/${list.length}</span></summary>
      <ol>${list.map((p) => `
        <li><button data-id="${p.id}" aria-current="${p === current}">
          <span>${esc(p.title)}</span>
          <span class="tags">${difficulty(p.difficulty)}${p.school ? `<span class="pf" title="Pre-final problem ${p.school}">PF ${p.school}</span>` : ''}${isSolved(p.id) ? '<span class="done" aria-label="solved">✓</span>' : ''}</span>
        </button></li>`).join('')}</ol>
    </details></li>`;
  }).join('');
}
$('problem-list').addEventListener('click', (e) => {
  const id = e.target.closest('button')?.dataset.id;
  if (id) { location.hash = id; }
});
$('problem-list').addEventListener('toggle', (e) => {
  const m = e.target.dataset.module;
  if (m) e.target.open ? openModules.add(m) : openModules.delete(m);
}, true);

// "Day 3 · 2 of 5 done" bar plus the next unfinished problem of that day.
function planContext() {
  if (planDay === null) return null;
  const day = plan.days[planDay];
  const items = dayItems(day);
  if (!items.some((it) => it.id === current.id)) return null;
  const done = items.filter((it) => doneOnDay(it.id, planDay, it.retry)).length;
  const after = items.slice(items.findIndex((it) => it.id === current.id) + 1).concat(items);
  const next = after.find((it) => it.id !== current.id && !doneOnDay(it.id, planDay, it.retry));
  return { day, done, total: items.length, next: next && problems.find((p) => p.id === next.id) };
}
function renderPlanBar() {
  const ctx = planContext();
  $('plan-bar').hidden = !ctx;
  if (!ctx) return;
  $('plan-bar').innerHTML = `
    <a href="plan.html">Day ${planDay + 1}: ${esc(ctx.day.title)}</a>
    <span>${ctx.done} of ${ctx.total} done</span>
    ${ctx.next ? `<a class="btn small" href="#${ctx.next.id}">Next: ${esc(ctx.next.title)}</a>` : '<span class="day-done">Day complete</span>'}`;
}
addEventListener('hashchange', () => {
  current = byId(location.hash.slice(1)) ?? current;
  load();
});

// Tests that swap in a different data file say so, and show it.
const otherFiles = (t) => Object.entries(t.files ?? {}).map(([name, content]) =>
  `<details class="test-file"><summary>This test uses a different <code>${esc(name)}</code></summary><pre>${esc(content)}</pre></details>`).join('');

function ioBlock(t) {
  return `${otherFiles(t)}<div class="example">
    <div><h3>Input</h3><pre>${esc(show(t.input))}</pre></div>
    <div><h3>Output</h3><pre>${esc(t.output)}</pre></div>
  </div>`;
}

function filePreview(name) {
  const lines = files[name].split('\n');
  const count = lines.at(-1) === '' ? lines.length - 1 : lines.length;
  const preview = lines.slice(0, 12).join('\n') + (count > 12 ? `\n… ${count - 12} more lines` : '');
  return `<details class="file"><summary><code>${esc(name)}</code> <span>${count} lines</span></summary><pre>${esc(preview)}</pre></details>`;
}

// The level the problem needs first (its reference solution uses nothing later), then the module's pages.
function revise(p) {
  const n = problemLevel[p.id];
  const needs = n ? [[`level-${n}`, `Level ${n}: ${levelTitle[n]}`, 'The reference solution uses nothing past this level']] : [];
  return [...needs, ...moduleOf(p).read.filter(([id]) => id !== `level-${n}`)];
}

function load() {
  store.set('last', current.id);
  if (location.hash.slice(1) !== current.id) history.replaceState(null, '', '#' + current.id);
  document.title = `${current.title} · Vertical World`;
  const kind = current.school ? `Pre-final problem ${current.school}` : current.module === 'basics' ? 'Warm-up' : 'Drill';
  $('problem').innerHTML = `
    <div class="plan-bar" id="plan-bar" hidden></div>
    <h1>${esc(current.title)}</h1>
    <p class="meta">${difficulty(current.difficulty)} ${difficultyLabel(current.difficulty)} · ${kind} · ${esc(moduleOf(current).title)}${isSolved(current.id) ? ' · solved' : ''}</p>
    <p class="revise">Revise: ${revise(current).map(([id, label, tip]) => `<a href="learn.html#${id}"${tip ? ` title="${esc(tip)}"` : ''}>${esc(label)}</a>`).join('')}</p>
    ${current.note ? `<p class="callout">${inline(current.note)}</p>` : ''}
    <h2>Task</h2>
    ${current.description.map((d) => `<p>${inline(d)}</p>`).join('')}
    ${current.files ? `<h2>Files your program can open</h2>${current.files.map(filePreview).join('')}` : ''}
    <h2>Example</h2>
    ${current.tests.filter((t) => t.sample).map(ioBlock).join('')}
    ${current.tips ? `<details class="reveal"><summary>Watch out for (from your notes)</summary><ul>${current.tips.map((t) => `<li>${inline(t)}</li>`).join('')}</ul></details>` : ''}
    <details class="reveal"><summary>Reference solution</summary>
      <p class="reveal-warn">Try it yourself first. Reading the answer before you've struggled with it teaches much less.</p>
      <pre class="solution">${esc(current.solution)}</pre>
    </details>`;
  renderPlanBar();
  const hidden = current.tests.filter((t) => !t.sample).length;
  $('tests').innerHTML = `<p>These are the sample cases.${hidden ? ` Submit also runs ${hidden} hidden ones.` : ''}</p>`
    + current.tests.filter((t) => t.sample).map(ioBlock).join('');
  $('results').innerHTML = '<p>Run the samples or submit your code to see results here.</p>';
  $('console-out').textContent = 'Nothing has run yet.';
  $('console-out').className = 'console-out';
  $('stdin').value = current.tests[0].input;
  $('pseudo').value = store.get('pseudo.' + current.id, '');
  renderLog();
  setStatus(python.status.ready ? 'Python ready' : 'Loading Python…');
  // Start blank. Code that is still exactly the old starter line was only auto-saved by a visit, so blank it too.
  const saved = store.get('code.' + current.id, '');
  editor.setValue(saved === current.starter ? '' : saved);
  editor.clearHistory();
  editor.setCursor(editor.lineCount(), 0);
  renderList();
  openTab('t-results');
}

/* Python runner (js/python.js: stopped after a time limit) */
const TIME_LIMIT_MS = 5000;
python.on('ready', () => { if (!buttons[0].disabled) setStatus('Python ready'); });
python.on('error', (message) => setStatus(message));
// Resolves with one { output, error } per input, or null if the time limit hit.
const runPython = (code, inputs, files = {}, testFiles = []) =>
  python.run({ code, inputs, files, testFiles }, TIME_LIMIT_MS, (text) => setStatus(text + '…')); // downloading a library
const setStatus = (s) => { $('status').textContent = s; };
const buttons = ['run', 'submit', 'run-console', 'reset'].map($);
const busy = (on) => buttons.forEach((b) => { b.disabled = on; });
const TIMEOUT_HELP = `Your code ran longer than ${TIME_LIMIT_MS / 1000} seconds. Look for a loop that never ends.`;

// Names the likely mistake (site/mistakes.py, the same sorting the Progress page counts). Hidden until the
// student asks, so they can find it themselves first.
const REVEAL = '<button class="btn small" id="reveal-mistake" aria-expanded="false" aria-controls="mistake" hidden>Reveal the mistake</button>';
const MISTAKE_BOX = '<div class="mistake" id="mistake" role="note" hidden></div>';
let runNo = 0;
async function showMistake(fail, run) {
  const m = await python.classify(fail);
  const box = $('mistake'), button = $('reveal-mistake');
  if (!m || !box || run !== runNo) return; // a newer run replaced these results
  box.innerHTML = `<p class="mistake-kind"><span class="mistake-group">${esc(m.groupTitle)}</span>${esc(m.title)}</p>
    ${m.detail ? `<p class="mistake-detail">${inline(m.detail)}</p>` : ''}
    <p class="mistake-tip"><b>Tip:</b> ${inline(m.tip)}</p>
    <p class="mistake-links">${m.learn ? `<a href="learn.html#${esc(m.learn)}">Revise: ${esc(m.learnLabel)}</a>` : ''}
      <a href="progress.html#mistakes">See all your mistakes</a></p>`;
  button.hidden = false;
  button.addEventListener('click', () => {
    box.hidden = !box.hidden;
    button.setAttribute('aria-expanded', String(!box.hidden));
    button.textContent = box.hidden ? 'Reveal the mistake' : 'Hide the mistake';
    if (!box.hidden && m.line && !errorLine && editor.getValue() === fail.code) markErrorLine(null, m.line);
  });
}

let lastFailure = '';
async function submit(samplesOnly) {
  if (buttons[0].disabled) return; // Ctrl+Enter while something is already running
  const tests = samplesOnly ? current.tests.filter((t) => t.sample) : current.tests;
  busy(true);
  setStatus(samplesOnly ? 'Running samples…' : 'Submitting…');
  openTab('t-results');
  const code = editor.getValue();
  const run = ++runNo;
  const mode = samplesOnly ? 'samples' : 'submit';
  try {
    const results = await runPython(code, tests.map((t) => t.input), filesOf(current), tests.map((t) => t.files ?? {}));
    if (!results) {
      $('results').innerHTML = `<div class="result-head"><p class="summary-line fail">Time limit exceeded</p>${REVEAL}</div>
        <p>${TIMEOUT_HELP}</p>${MISTAKE_BOX}`;
      lastFailure = 'The program ran past the time limit (likely an infinite loop).';
      const fail = { code, timeout: true };
      logAttempt({ id: current.id, mode, passed: 0, total: tests.length, fail });
      showMistake(fail, run);
      flash(false);
      return setStatus('Stopped: time limit');
    }
    const rows = tests.map((t, i) => ({ t, r: results[i], ok: !results[i].error && sameOutput(t.output, results[i].output) }));
    const passed = rows.filter((x) => x.ok).length;
    const all = passed === rows.length;
    const firstBad = rows.find((x) => !x.ok);
    const fail = firstBad && { code, input: firstBad.t.input, expected: firstBad.t.output, got: firstBad.r.output, error: firstBad.r.error ?? '' };
    logAttempt({ id: current.id, mode, passed, total: rows.length, ...(fail && { fail }) });
    if (all && !samplesOnly) { markSolved(current.id); renderList(); renderPlanBar(); }
    lastFailure = firstBad ? `Input: ${show(firstBad.t.input)}\nExpected:\n${firstBad.t.output}\nGot:\n${firstBad.r.output}${firstBad.r.error ? '\nError:\n' + firstBad.r.error : ''}` : '';
    markErrorLine(rows.find((x) => x.r.error)?.r.error);
    $('results').innerHTML = `
      <div class="result-head">
        <p class="summary-line ${all ? 'pass' : 'fail'}">${passed} of ${rows.length} passed${all && !samplesOnly ? '. Solved!' : ''}</p>
        ${firstBad ? `${REVEAL}<button class="btn small" id="explain">Ask the AI why it failed</button>` : ''}
        ${all && !samplesOnly && planContext()?.next ? `<a class="btn small primary" href="#${planContext().next.id}">Next in Day ${planDay + 1}: ${esc(planContext().next.title)}</a>` : ''}
      </div>
      ${fail ? MISTAKE_BOX : ''}
      ${rows.map(({ t, r, ok }, i) => `
        <details class="result ${ok ? 'pass' : 'fail'}" ${ok ? '' : 'open'}>
          <summary><span>Case ${i + 1}${t.sample ? '' : ' (hidden)'}</span><span class="tag">${ok ? 'Passed' : r.error ? 'Error' : 'Wrong output'}</span></summary>
          <div class="io">
            <div><h4>Input</h4><pre>${esc(show(t.input))}${t.files ? `\n(with a different ${esc(Object.keys(t.files).join(', '))})` : ''}</pre></div>
            <div><h4>Expected</h4><pre>${esc(t.output)}</pre></div>
            <div><h4>Your output</h4><pre>${esc(show(r.output))}</pre></div>
            ${r.error ? `<div class="wide"><h4>Error</h4><pre>${esc(r.error)}</pre></div>` : ''}
          </div>
        </details>`).join('')}`;
    $('explain')?.addEventListener('click', () =>
      askAI('explain', `${editor.getValue()}\n\nRESULT:\n${lastFailure}`));
    if (fail) showMistake(fail, run);
    flash(all);
    setStatus(all ? 'All passed' : `${rows.length - passed} failed`);
  } catch (e) {
    $('results').innerHTML = `<p class="summary-line fail">Python is not available</p><p>${esc(e.message)}</p>`;
    setStatus('Python failed to load');
  } finally {
    busy(false);
  }
}

/* Console: run once with the student's own input, no grading */
async function runConsole() {
  const out = $('console-out');
  busy(true);
  setStatus('Running…');
  openTab('t-console');
  try {
    const results = await runPython(editor.getValue(), [$('stdin').value], filesOf(current));
    if (!results) {
      out.textContent = TIMEOUT_HELP;
      out.className = 'console-out error';
      return setStatus('Stopped: time limit');
    }
    const [{ output, error }] = results;
    const gap = error && output && !output.endsWith('\n') ? '\n' : '';
    out.textContent = output + gap + (error ?? '') || '(your program printed nothing)';
    out.className = error ? 'console-out error' : 'console-out';
    markErrorLine(error);
    setStatus(error ? 'Finished with an error' : 'Finished');
  } catch (e) {
    out.textContent = e.message;
    out.className = 'console-out error';
    setStatus('Python failed to load');
  } finally {
    busy(false);
  }
}

/* AI tutor (local Claude Code or Codex CLI via server.py) */
function problemText() {
  const samples = current.tests.filter((t) => t.sample).map((t) => `Input: ${show(t.input)}\nOutput:\n${t.output}`).join('\n\n');
  return `${current.title}\n${current.description.join('\n').replace(/`/g, '')}\n\n${samples}`;
}

// The tutor log is kept per problem so earlier answers are still there when you come back.
const KIND_LABEL = { pseudo: 'Plan check', hint: 'Hint', explain: 'Why it failed' };
const MODEL_LABEL = { '': 'Default model', haiku: 'Haiku 5.5', sonnet: 'Sonnet 5.5', opus: 'Opus 5.5', fable: 'Fable 5.2' };
const EFFORT_LABEL = { '': 'default effort', low: 'low effort', medium: 'medium effort', high: 'high effort', xhigh: 'extra high effort', max: 'max effort' };
const aiModel = $('ai-model'), aiEffort = $('ai-effort');

// The helper chat (click the 3D gem). Inserted code goes on its own line at the cursor.
initHelper({
  problem: () => current,
  problemText,
  code: () => editor.getValue(),
  model: () => aiModel.value,
  effort: () => aiEffort.value,
  modelSelect: aiModel,
  effortSelect: aiEffort,
  insert(code) {
    const cur = editor.getCursor();
    const line = editor.getLine(cur.line);
    if (line.trim()) editor.setCursor({ line: cur.line, ch: line.length });
    editor.replaceSelection((line.trim() ? '\n' : '') + code + '\n');
    editor.focus();
  },
  replace(code) {
    editor.setValue(code + '\n');
    editor.focus();
  },
  hasFunction: (name) => !!findFunction(editor.getValue(), name),
  // Swap one function in place (only its lines change, so undo and the rest of the file are untouched).
  replaceFunction(code) {
    const src = editor.getValue();
    const at = findFunction(src, functionName(code));
    const next = at && replaceFunction(src, code);
    if (!next) return false;
    const lines = next.split('\n');
    const fresh = lines.slice(at.start, lines.length - (src.split('\n').length - at.end));
    editor.replaceRange(fresh.join('\n'), { line: at.start, ch: 0 }, { line: at.end - 1, ch: editor.getLine(at.end - 1).length });
    editor.focus();
    return true;
  },
});
aiModel.value = store.get('ai.model', '');
aiEffort.value = store.get('ai.effort', '');
aiModel.addEventListener('change', () => store.set('ai.model', aiModel.value));
aiEffort.addEventListener('change', () => store.set('ai.effort', aiEffort.value));

const pending = new Map(); // problem id -> pending entry (one request per problem at a time)
const logOf = (id) => store.get('ailog.' + id, []);

function renderLog() {
  const entries = [...(pending.has(current.id) ? [pending.get(current.id)] : []), ...logOf(current.id)];
  $('ai-log').innerHTML = entries.length ? entries.map((m) => `
    <li class="msg msg-${m.kind}${m.error ? ' error' : ''}${m.pending ? ' pending' : ''}">
      <header><strong>${KIND_LABEL[m.kind]}</strong>
        <span>${esc(MODEL_LABEL[m.model] ?? m.model)} · ${EFFORT_LABEL[m.effort] ?? m.effort} · ${new Date(m.at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</span>
      </header>
      <p>${inline(m.text)}</p>
    </li>`).join('') : '<li class="ai-empty">Ask for a hint or check your plan. Answers collect here, newest first.</li>';
  const waiting = pending.has(current.id);
  $('hint').disabled = $('check-plan').disabled = waiting;
}

async function askAI(kind, text) {
  openTab('e-ai');
  const id = current.id;
  if (pending.has(id)) return;
  const entry = { kind, model: aiModel.value, effort: aiEffort.value, at: Date.now() };
  if (!text.trim()) {
    entry.error = true;
    entry.text = kind === 'pseudo' ? 'Write a few steps in "Your plan" first.' : 'Write some code first.';
    store.set('ailog.' + id, [entry, ...logOf(id)].slice(0, 30));
    return renderLog();
  }
  pending.set(id, { ...entry, pending: true, text: 'Thinking… usually 5–30 seconds, longer at high effort' });
  renderLog();
  try {
    const res = await fetch('/api/ai', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind, problem: problemText(), text, model: entry.model, effort: entry.effort }),
    });
    const data = await res.json().catch(() => ({ error: `The server answered ${res.status}. Restart the site.` }));
    if (!res.ok) throw new Error(data.error);
    entry.text = data.reply;
  } catch (e) {
    entry.error = true;
    entry.text = e.message === 'Failed to fetch' ? 'Could not reach the local server. Start it with site\\start.bat (Windows) or ./site/start.sh (Linux).' : e.message;
  } finally {
    pending.delete(id);
    store.set('ailog.' + id, [entry, ...logOf(id)].slice(0, 30));
    if (current.id === id) renderLog();
  }
}

$('run').addEventListener('click', () => submit(true));
$('submit').addEventListener('click', () => submit(false));
$('run-console').addEventListener('click', runConsole);
$('hint').addEventListener('click', () => askAI('hint', editor.getValue()));
$('check-plan').addEventListener('click', () => askAI('pseudo', $('pseudo').value));
$('clear-log').addEventListener('click', () => {
  if (!logOf(current.id).length || !confirm('Clear the tutor answers for this problem?')) return;
  store.set('ailog.' + current.id, []);
  renderLog();
});
$('reset').addEventListener('click', () => {
  if (!confirm("Clear your code for this problem? This can't be undone.")) return;
  editor.setValue('');
  editor.focus();
});

load();
