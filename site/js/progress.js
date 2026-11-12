// Progress shared by the practice and plan pages: when each problem was last solved.
import { plan, problems } from './problems.js?v=5';

const KEY = 'vw.solvedAt';
const DAY_MS = 86_400_000;

function load() {
  const saved = JSON.parse(localStorage.getItem(KEY) ?? 'null');
  if (saved) return saved;
  // Older versions stored a plain list of solved ids; count those as solved long ago.
  const old = JSON.parse(localStorage.getItem('vw.solved') ?? '[]');
  return Object.fromEntries(old.map((id) => [id, 0]));
}

let solvedAt = load();

export const isSolved = (id) => id in solvedAt;

export function markSolved(id) {
  solvedAt = { ...load(), [id]: Date.now() };
  localStorage.setItem(KEY, JSON.stringify(solvedAt));
}

// Plan dates are local calendar days: day 1 is plan.start.
const [y, m, d] = plan.start.split('-').map(Number);
export const dayStart = (i) => new Date(y, m - 1, d + i);

// 0-based index of today in the plan (can be negative before it starts, or past the end).
export function todayIndex(now = new Date()) {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((today - dayStart(0)) / DAY_MS);
}

// New drills count once solved at all. Pre-final problems and retries are meant to be redone,
// so they only count when solved on or after that day's date.
const school = new Set(problems.filter((p) => p.school).map((p) => p.id));
export const doneOnDay = (id, i, retry = false) =>
  isSolved(id) && (!(retry || school.has(id)) || solvedAt[id] >= dayStart(i).getTime());

// Difficulty 1-3 as three small bars, with a text label for screen readers and hover.
const LEVELS = ['', 'Easy', 'Medium', 'Hard'];
export const difficulty = (d) =>
  `<span class="diff d${d}" title="${LEVELS[d]} (${d} of 3)" aria-label="Difficulty: ${LEVELS[d]}, ${d} of 3" role="img"><i></i><i></i><i></i></span>`;
export const difficultyLabel = (d) => LEVELS[d];

export const dayItems = (day) => [
  ...day.items.map((id) => ({ id, retry: false })),
  ...(day.retry ?? []).map((id) => ({ id, retry: true })),
];
