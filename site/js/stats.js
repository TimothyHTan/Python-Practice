// Progress page: draws the analytics that notes_store.py computes from Documents\python notes.
import { problems } from './problems.js?v=5';
import { onSync } from './sync.js?v=5';
import { highlight } from './palette.js?v=5';

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const title = Object.fromEntries(problems.map((p) => [p.id, p.title]));
const TOP = 12;
const lessonsTotal = 13;

// "math.sqrt()" -> "math sqrt": the words the Function finder filter understands.
const finderQuery = (name) => name.replace(/[().]/g, ' ').trim();

function bars(list, max, link) {
  return list.map((f) => {
    const where = f.problems.map((id) => title[id] ?? id);
    const tip = `Used ${f.uses} time${f.uses === 1 ? '' : 's'} in ${where.length} problem${where.length === 1 ? '' : 's'}: ${where.slice(0, 6).join(', ')}${where.length > 6 ? ', …' : ''}`;
    const inner = `<span class="bar-name">${esc(f.name)}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${Math.max(2, (f.uses / max) * 100)}%"></span></span>
      <span class="bar-value">${f.uses}</span><span class="bar-tip" role="tooltip">${esc(tip)}</span>`;
    return `<li>${link ? `<a class="bar-row" href="learn.html?q=${encodeURIComponent(finderQuery(f.name))}#functions" aria-label="${esc(tip)}. Show examples.">${inner}</a>`
      : `<div class="bar-row" tabindex="0" aria-label="${esc(f.name)}: ${esc(tip)}">${inner}</div>`}</li>`;
  }).join('');
}

const inline = (s) => esc(s).replace(/`([^`]+)`/g, '<code>$1</code>');
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

// Code with the line the mistake points at marked. Highlighted line by line, which is fine for short practice code.
const codeWithLine = (code, line) => code.split('\n').map((l, i) =>
  `<span class="mk-line${i + 1 === line ? ' hit' : ''}"><span class="mk-ln">${i + 1}</span>${highlight(l) || ' '}</span>`).join('');

function kindRow(k) {
  const ex = k.example;
  const solvedNote = k.fixed ? `fixed later in ${k.fixed} of ${plural(k.problems.length, 'problem')}` : `in ${plural(k.problems.length, 'problem')}`;
  return `<li><details class="mk-kind">
    <summary><span class="mk-title">${esc(k.title)}</span><span class="mk-meta">${solvedNote}</span><span class="mk-count">${k.count}×</span></summary>
    <div class="mk-body">
      <p class="mk-tip"><b>How to avoid it:</b> ${inline(k.tip)}${k.learn ? ` <a class="mk-revise" href="learn.html#${esc(k.learn)}">Revise: ${esc(k.learnLabel)}</a>` : ''}</p>
      <p class="mk-ex-head">Latest: <a href="practice.html#${esc(ex.problem)}">${esc(title[ex.problem] ?? ex.problem)}</a> · ${esc(fmtTime(ex.time))}</p>
      ${ex.detail ? `<p class="mk-detail">${inline(ex.detail)}</p>` : ''}
      ${ex.code ? `<pre class="cm-s-vw code-view mk-code"><code>${codeWithLine(ex.code, ex.line)}</code></pre>` : ''}
      ${k.problems.length > 1 ? `<p class="mk-also">Also in: ${k.problems.filter((id) => id !== ex.problem).map((id) => `<a href="practice.html#${esc(id)}">${esc(title[id] ?? id)}</a>`).join(', ')}</p>` : ''}
    </div></details></li>`;
}

function renderMistakes(m) {
  if (!m?.total) {
    $('mk-body').innerHTML = '<p class="bars-empty">No mistakes recorded yet. From now on every failed run on the Practice page is sorted here, with your code, so you can see what you get wrong most.</p>';
    return;
  }
  const max = m.groups[0].count;
  $('mk-body').innerHTML = `<ol class="mk-groups">${m.groups.map((g, i) => `<li><details class="mk-group"${i === 0 ? ' open' : ''}>
    <summary class="bar-row"><span class="bar-name">${esc(g.title)}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${Math.max(2, (g.count / max) * 100)}%"></span></span>
      <span class="bar-value">${g.count}</span></summary>
    <ol class="mk-kinds">${g.kinds.map(kindRow).join('')}</ol></details></li>`).join('')}</ol>`;
}

const fmtTime = (iso) => (iso ? new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : '');

function render(state) {
  const a = state.analytics;
  $('saved-to').innerHTML = state.ok
    ? `<span class="dot ok" aria-hidden="true"></span><span>Saved to <code>${esc(state.folder)}</code> at ${state.savedAt.toLocaleTimeString([], { timeStyle: 'short' })}</span>
       <button class="key" type="button" id="open-folder">Open folder</button>`
    : `<span class="dot bad" aria-hidden="true"></span><span>${esc(state.error)} Start it with <code>site\\start.bat</code> (Windows) or <code>./site/start.sh</code> (Linux), then reload.</span>`;
  $('open-folder')?.addEventListener('click', () => fetch('/api/open-folder', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }));
  if (!a) { $('summary').textContent = 'Your analytics need the local server.'; return; }

  const submits = a.attempts.reduce((n, r) => n + r.submits, 0);
  const runs = a.attempts.reduce((n, r) => n + r.runs, 0);
  const lessons = JSON.parse(localStorage.getItem('vw.lessons.done') ?? '[]').length;
  $('summary').textContent = `You've solved ${a.solved} of ${problems.length} problems, written code for ${a.problemsWithCode}, `
    + `run the samples ${runs} time${runs === 1 ? '' : 's'} and submitted ${submits} time${submits === 1 ? '' : 's'}. `
    + `${lessons} of ${lessonsTotal} lessons are done.`
    + (a.mistakes?.total ? ` Your most common mistake is “${a.mistakes.groups.flatMap((g) => g.kinds).sort((x, y) => y.count - x.count)[0].title}”.` : '')
    + (a.unparsable.length ? ` ${a.unparsable.length} problem${a.unparsable.length === 1 ? ' has' : 's have'} a syntax error, so ${a.unparsable.length === 1 ? 'it isn\'t' : 'they aren\'t'} counted below.` : '');

  renderMistakes(a.mistakes);
  const byProblem = a.mistakes?.byProblem ?? {};

  const fns = a.functions;
  const max = fns[0]?.uses ?? 1;
  $('fn-bars').innerHTML = fns.length ? bars(fns.slice(0, TOP), max, true)
    : '<li class="bars-empty">No code yet. Write code on the Practice page and the functions you use show up here.</li>';
  $('fn-more').hidden = fns.length <= TOP;
  $('fn-more').querySelector('summary').textContent = `${fns.length - TOP} more functions`;
  $('fn-rest').innerHTML = bars(fns.slice(TOP), max, true);

  const cx = a.constructs;
  $('cx-bars').innerHTML = cx.length ? bars(cx, cx[0].uses, false) : '<li class="bars-empty">Nothing yet.</li>';

  $('attempts').innerHTML = a.attempts.length
    ? `<thead><tr><th scope="col">Problem</th><th scope="col" class="num">Sample runs</th><th scope="col" class="num">Submits</th>
        <th scope="col" class="num">Passed submits</th><th scope="col">Main mistake</th><th scope="col">Status</th><th scope="col">Last try</th></tr></thead>
       <tbody>${a.attempts.map((r) => `<tr>
        <td><a href="practice.html#${esc(r.id)}">${esc(title[r.id] ?? r.id)}</a></td>
        <td class="num">${r.runs}</td><td class="num">${r.submits}</td><td class="num">${r.passedSubmits}</td>
        <td class="mk-cell">${byProblem[r.id] ? `${esc(byProblem[r.id][0].title)}${byProblem[r.id][0].count > 1 ? ` <span class="mk-n">${byProblem[r.id][0].count}×</span>` : ''}` : '<span class="mk-none">–</span>'}</td>
        <td>${r.solved ? '<span class="status-pill solved">✓ Solved</span>' : '<span class="status-pill open">○ Not yet</span>'}</td>
        <td class="when">${esc(fmtTime(r.last))}</td></tr>`).join('')}</tbody>`
    : '<tbody><tr><td class="bars-empty">No runs yet. Every "Run samples" and "Submit" on the Practice page is recorded here.</td></tr></tbody>';
}

onSync(render);
