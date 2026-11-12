import './sync.js?v=5'; // restores solved problems from Documents\python notes if this browser lost them
import { plan, problems, modules, checklist } from './problems.js?v=5';
import { isSolved, doneOnDay, dayItems, dayStart, todayIndex, difficulty } from './progress.js?v=5';

const $ = (id) => document.getElementById(id);
const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const inline = (s) => esc(s).replace(/`([^`]+)`/g, '<code>$1</code>');
const byId = Object.fromEntries(problems.map((p) => [p.id, p]));
const fmt = (d, opts) => d.toLocaleDateString('en-GB', opts);

const today = todayIndex();
const last = plan.days.length - 1;
// The day to point at: today, or day 1 before the plan starts.
const focus = today < 0 ? 0 : Math.min(today, last);

$('plan-dates').textContent =
  `${fmt(dayStart(0), { weekday: 'long', day: 'numeric' })} to ${fmt(dayStart(last), { weekday: 'long', day: 'numeric', month: 'long' })}. `
  + 'Day 1 is the big one: nine pre-final problems again, from a blank editor, easiest first. After that, a couple of drills a day plus the pre-final problems on the same topic, with the hardest three saved for days 5 and 6, and a timed mock final at the end. The bars next to each problem show how hard it is: one is easy, three is hard.';

function whenLabel(i) {
  if (i === today) return 'Today';
  if (i === today + 1) return 'Tomorrow';
  if (i < today) return 'Past';
  return '';
}

let doneAll = 0, totalAll = 0;
$('days').innerHTML = plan.days.map((day, i) => {
  const items = dayItems(day);
  const done = items.filter((it) => doneOnDay(it.id, i, it.retry)).length;
  doneAll += done;
  totalAll += items.length;
  const date = dayStart(i);
  const when = whenLabel(i);
  const classes = ['day', day.heavy && 'heavy', i === focus && 'focus', done === items.length && 'complete'].filter(Boolean).join(' ');
  return `<li class="${classes}" id="day-${i + 1}">
    <div class="day-date">
      <span class="dow">${fmt(date, { weekday: 'short' })}</span>
      <span class="dom">${date.getDate()}</span>
      <span class="mon">${fmt(date, { month: 'short' })}</span>
      ${when ? `<span class="when">${when}</span>` : ''}
    </div>
    <div class="day-body">
      <h2><span class="day-no">Day ${i + 1}</span> ${esc(day.title)}</h2>
      <p class="day-meta">${day.heavy ? '<span class="heavy-tag">Heavy day</span>' : ''}<span>${esc(day.time)}</span><span>${done} of ${items.length} done</span></p>
      <p class="day-focus">${esc(day.focus)}</p>
      ${day.read ? `<p class="revise">Read first: ${day.read.map(([id, label]) => `<a href="learn.html#${id}">${esc(label)}</a>`).join('')}</p>` : ''}
      <ol class="tasks">${items.map(({ id, retry }) => {
        const p = byId[id];
        const ok = doneOnDay(id, i, retry);
        return `<li><a class="task${ok ? ' done' : ''}" href="practice.html?day=${i + 1}#${id}">
          <span class="check" aria-label="${ok ? 'done' : 'not done'}"></span>
          <span class="task-title">${esc(p.title)}</span>
          ${difficulty(p.difficulty)}
          ${p.school ? `<span class="pf">PF ${p.school}</span>` : ''}
          ${retry ? '<span class="retry">Retry</span>' : ''}
        </a></li>`;
      }).join('')}</ol>
    </div>
  </li>`;
}).join('');

$('total-bar').style.width = `${(doneAll / totalAll) * 100}%`;
$('total-text').textContent = `${doneAll} of ${totalAll} tasks done`;

/* Checklist with ticks saved in the browser */
const CHECK_KEY = 'vw.checklist';
const ticks = new Set(JSON.parse(localStorage.getItem(CHECK_KEY) ?? '[]'));
$('checklist').innerHTML = checklist.map((item, i) => `
  <li><label><input type="checkbox" data-i="${i}" ${ticks.has(i) ? 'checked' : ''}><span>${inline(item)}</span></label></li>`).join('');
$('checklist').addEventListener('change', (e) => {
  const i = Number(e.target.dataset.i);
  e.target.checked ? ticks.add(i) : ticks.delete(i);
  localStorage.setItem(CHECK_KEY, JSON.stringify([...ticks]));
});
$('clear-checks').addEventListener('click', () => {
  ticks.clear();
  localStorage.setItem(CHECK_KEY, '[]');
  document.querySelectorAll('#checklist input').forEach((c) => { c.checked = false; });
});

/* Module progress */
$('module-progress').innerHTML = modules.map((m) => {
  const list = problems.filter((p) => p.module === m.id);
  const done = list.filter((p) => isSolved(p.id)).length;
  const next = list.find((p) => !isSolved(p.id)) ?? list[0];
  return `<li><a href="practice.html#${next.id}">
    <span>${esc(m.title)}</span><span class="progress-count">${done}/${list.length}</span>
    <span class="bar" aria-hidden="true"><span style="width:${(done / list.length) * 100}%"></span></span>
  </a></li>`;
}).join('');

if (focus > 0) document.getElementById(`day-${focus + 1}`).scrollIntoView({ block: 'center' });
