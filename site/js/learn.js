import { lessons } from './lessons.js?v=5';
import { categories, recipes } from './learn-index.js?v=5';
import { rank } from './search.js?v=5';
import { highlight, openSearch } from './palette.js?v=5';
import { saveSoon, onSync } from './sync.js?v=5';
import { isSolved } from './progress.js?v=5';
import { openNoteMenu } from './addnote.js?v=5';

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const DONE_KEY = 'vw.lessons.done';
const LEVELS = lessons.filter((l) => l.num).length;
const catTitle = Object.fromEntries(categories.map((c) => [c.id, c.title]));
const lessonTitle = Object.fromEntries(lessons.map((l) => [l.id, l.num ? `Level ${l.num}: ${l.title}` : l.title]));

let done = JSON.parse(localStorage.getItem(DONE_KEY) ?? '[]');
let shownLesson = null;

/* Sidebar */
$('side-cats').innerHTML = `<li><a href="#functions" data-route="functions">All functions <span class="count">${recipes.length}</span></a></li>`
  + categories.map((c) => `<li><a href="#cat-${c.id}" data-route="cat-${c.id}">${esc(c.title)} <span class="count">${recipes.filter((r) => r.cat === c.id).length}</span></a></li>`).join('');

function paintSide() {
  $('side-lessons').innerHTML = lessons.map((l) => `<li><a href="#${l.id}" data-route="${l.id}" class="${done.includes(Number(l.num)) ? 'done' : ''}">
    ${l.num ? `<span class="lvl ink-${l.ink}">${l.num}</span>` : ''}<span class="lt">${esc(l.title)}${l.project ? `<small>${esc(l.project)}</small>` : ''}</span>
    ${done.includes(Number(l.num)) ? '<span class="tick" aria-label="done">✓</span>' : ''}</a></li>`).join('');
  $('lessons-done').textContent = `${done.length}/${LEVELS}`;
}
$('side-search').addEventListener('click', () => openSearch());

/* Function finder */
const recipeDocs = recipes.map((r) => ({ kind: 'fn', recipe: r, title: r.title, keys: r.keys, where: catTitle[r.cat], code: r.code, text: r.note }));

const catOf = Object.fromEntries(categories.map((c) => [c.id, c]));
const EXAMPLES = ['letters to numbers', 'remove duplicates', 'read a csv', 'round to 2 decimals', 'days between dates', 'reverse a string'];
$('ask-try').innerHTML = `<span>Try</span>${EXAMPLES.map((e) => `<button class="key" type="button" data-q="${esc(e)}">${esc(e)}</button>`).join('')}`;

const card = (r, showCat) => `
  <article class="recipe" id="r-${r.id}">
    <header>
      ${showCat ? `<span class="recipe-glyph" title="${esc(catOf[r.cat].title)}">${esc(catOf[r.cat].glyph)}</span>` : ''}
      <h3>${esc(r.title)}</h3>
      <button class="key" type="button" data-addnote="${r.id}">Add to notes</button>
      <button class="key copy" type="button">Copy</button>
    </header>
    <div class="run">
      <pre class="cm-s-vw code-view"><code>${highlight(r.code)}</code></pre>
      <div class="out"><span>Output</span><pre>${esc(r.output)}</pre></div>
    </div>
    ${r.note || r.files.length || r.lesson ? `<p class="more">${r.note ? `<span>${esc(r.note)}</span>` : ''}
      ${r.files.map((f) => `<span>Reads <code>${esc(f)}</code>, one of the practice data files.</span>`).join('')}
      ${r.lesson ? `<a href="#${r.lesson}">${esc(lessonTitle[r.lesson])}</a>` : ''}</p>` : ''}
  </article>`;

function renderFinder() {
  const q = $('finder-q').value.trim();
  if (!q) {
    $('finder-body').innerHTML = categories.map((c) => {
      const list = recipes.filter((r) => r.cat === c.id);
      return `
      <section class="cat" id="cat-${c.id}">
        <div class="cat-mark">
          <span class="glyph" aria-hidden="true">${esc(c.glyph)}</span>
          <h2>${esc(c.title)}</h2>
          <p>${esc(c.blurb)}</p>
          <span class="n">${list.length} examples</span>
        </div>
        <div class="cat-list">${list.map((r) => card(r)).join('')}</div>
      </section>`;
    }).join('');
    $('finder-count').textContent = '';
    return;
  }
  const found = rank(q, recipeDocs, 100).map((d) => d.recipe);
  $('finder-count').textContent = found.length ? `${found.length} example${found.length === 1 ? '' : 's'} for “${q}”, best first` : '';
  $('finder-body').innerHTML = found.length
    ? `<div class="cat-list solo">${found.map((r) => card(r, true)).join('')}</div>`
    : `<p class="finder-none">Nothing in the Function finder matches “${esc(q)}”. Try one simpler word, like <b>split</b>, or <button class="link" type="button" id="search-all">search lessons, problems and notes too</button>.</p>`;
}
$('finder-q').addEventListener('input', renderFinder);
$('ask-try').addEventListener('click', (e) => {
  const b = e.target.closest('[data-q]');
  if (!b) return;
  $('finder-q').value = b.dataset.q;
  renderFinder();
  $('finder-q').focus();
});
$('finder-body').addEventListener('click', (e) => {
  if (e.target.id === 'search-all') return openSearch($('finder-q').value);
  const b = e.target.closest('[data-addnote]');
  const r = b && recipes.find((x) => x.id === b.dataset.addnote);
  if (r) openNoteMenu(b, {
    title: catOf[r.cat].title, heading: r.title, query: `${r.title} ${r.keys}`, source: 'the Function finder',
    text: '```python\n' + r.code + '\n```\nOutput:\n```\n' + r.output + '\n```' + (r.note ? '\n' + r.note : ''),
  });
});

/* Lessons */
function showLesson(lesson) {
  if (shownLesson === lesson.id) return;
  shownLesson = lesson.id;
  const el = $('lesson');
  el.className = `lesson ink-${lesson.ink}`;
  el.innerHTML = lesson.html;
  for (const code of el.querySelectorAll('code.language-python')) {
    code.innerHTML = highlight(code.textContent);
    code.parentElement.classList.add('cm-s-vw');
  }
  for (const a of el.querySelectorAll('a[href^="http"]')) { a.target = '_blank'; a.rel = 'noopener'; }
  paintProgress();
  paintConnections();
}

// The "Practice and connections" part of a level: ticks on solved problems, and the student's own mistakes
// (from the Progress analytics) whose lesson link points into this level.
let myMistakes = [];
const levelOf = (anchor) => lessons.find((l) => l.id === anchor || l.html.includes(`id="${anchor}"`))?.num;
function paintConnections() {
  const el = $('lesson');
  for (const li of el.querySelectorAll('[data-problem]')) li.classList.toggle('solved', isSolved(li.dataset.problem));
  const card = el.querySelector('.ll-mistakes');
  if (!card) return;
  const mine = myMistakes.filter((k) => levelOf(k.learn) === card.dataset.level);
  card.hidden = !mine.length;
  card.querySelector('ul').innerHTML = mine.map((k) => `<li><a href="#${esc(k.learn)}">${esc(k.title)}</a> <span class="mk-n">${k.count}×</span></li>`).join('')
    + '<li><a class="ll-more" href="progress.html#mistakes">All your mistakes</a></li>';
}
onSync((state) => {
  myMistakes = (state.analytics?.mistakes?.groups ?? []).flatMap((g) => g.kinds).filter((k) => k.learn);
  if (shownLesson) paintConnections();
});

function paintProgress() {
  const el = $('lesson');
  for (const li of el.querySelectorAll('[data-level-item]')) li.classList.toggle('done', done.includes(Number(li.dataset.levelItem)));
  let next = 1;
  while (next <= LEVELS && done.includes(next)) next++;
  const cont = el.querySelector('#continue-btn');
  if (cont) {
    cont.textContent = next > LEVELS ? 'All levels done' : done.length ? `Continue with Level ${next}` : 'Start Level 1';
    cont.href = `#level-${Math.min(next, LEVELS)}`;
  }
  for (const btn of el.querySelectorAll('[data-complete]')) {
    const level = Number(btn.dataset.complete);
    btn.textContent = done.includes(level)
      ? (level >= LEVELS ? 'Back to the overview' : `Go to Level ${level + 1}`)
      : (level >= LEVELS ? 'Mark done and finish' : `Mark done and go to Level ${level + 1}`);
  }
  paintSide();
}

/* Routing: #functions, #cat-x, #r-x are the finder; anything else is a lesson or a heading inside one */
function route() {
  const id = decodeURIComponent(location.hash.slice(1)) || 'functions';
  const inFinder = id === 'functions' || id.startsWith('cat-') || id.startsWith('r-');
  let lesson = null;
  if (!inFinder) lesson = lessons.find((l) => l.id === id) ?? lessons.find((l) => l.html.includes(`id="${id}"`));
  $('finder').hidden = !!lesson;
  $('lesson').hidden = !lesson;
  if (lesson) showLesson(lesson);
  else if (id.startsWith('r-') && !document.getElementById(id)) { $('finder-q').value = ''; renderFinder(); }

  const target = id === 'functions' || id === lesson?.id ? null : document.getElementById(id);
  if (target) {
    target.scrollIntoView();
    target.classList.remove('flash');
    void target.offsetWidth; // restart the animation
    target.classList.add('flash');
  } else scrollTo(0, 0);

  const sideId = lesson ? lesson.id : id.startsWith('cat-') ? id : 'functions';
  document.querySelectorAll('.learn-side [data-route]').forEach((a) => a.toggleAttribute('aria-current', a.dataset.route === sideId));
  document.title = `${lesson ? lessonTitle[lesson.id] : 'Function finder'} · Learn · Vertical World`;
}

/* Copy buttons and "mark done" */
$('learn-main').addEventListener('click', async (e) => {
  const copy = e.target.closest('.copy');
  if (copy) {
    const code = copy.closest('.code, .recipe')?.querySelector('code');
    if (!code) return;
    await navigator.clipboard.writeText(code.textContent);
    copy.textContent = 'Copied';
    setTimeout(() => { copy.textContent = 'Copy'; }, 1500);
    return;
  }
  const complete = e.target.closest('[data-complete]');
  if (complete) {
    const level = Number(complete.dataset.complete);
    if (!done.includes(level)) { done = [...done, level].sort((a, b) => a - b); localStorage.setItem(DONE_KEY, JSON.stringify(done)); saveSoon(); }
    paintProgress();
    location.hash = level >= LEVELS ? 'start' : `level-${level + 1}`;
  }
});

$('finder-q').value = new URLSearchParams(location.search).get('q') ?? ''; // from the Progress page
renderFinder();
paintSide();
addEventListener('hashchange', route);
route();
