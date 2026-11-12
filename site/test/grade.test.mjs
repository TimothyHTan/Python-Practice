import assert from 'node:assert/strict';
import { sameOutput } from '../js/grade.js';
import { problems } from '../js/problems.js';

assert.ok(sameOutput('8', '8\n'));
assert.ok(sameOutput('a\nb', 'a  \r\nb\r\n\n'));
assert.ok(sameOutput('H\n\nw', 'H\n \nw')); // print(' ') counts as the blank line
assert.ok(!sameOutput('8', '9'));
assert.ok(!sameOutput('a\nb', 'a\n\nb'));

for (const p of problems) {
  assert.ok(p.id && p.title && p.tests.length, `problem ${p.id} is incomplete`);
  assert.ok(p.tests.some((t) => t.sample), `problem ${p.id} needs a sample test`);
}
assert.equal(new Set(problems.map((p) => p.id)).size, problems.length, 'duplicate problem id');
console.log('grade tests passed');

// Plan and data files must point at things that exist.
const { plan, files, modules } = await import('../js/problems.js');
for (const day of plan.days) for (const id of [...day.items, ...(day.retry ?? [])]) assert.ok(problems.some((p) => p.id === id), `plan: unknown ${id}`);
for (const p of problems) for (const f of p.files ?? []) assert.ok(files[f], `${p.id}: missing file ${f}`);
for (const p of problems) assert.ok(modules.some((m) => m.id === p.module), `${p.id}: unknown module`);
console.log('plan and files ok');

// Learn page: search finds the right function for plain-English questions, and every link target exists.
const { rank, noteDocs } = await import('../js/search.js');
const { recipes, categories, lessonDocs } = await import('../js/learn-index.js');
const { lessons } = await import('../js/lessons.js');
const fnDocs = recipes.map((r) => ({ kind: 'fn', id: r.id, title: r.title, keys: r.keys, where: r.cat, code: r.code, text: r.note }));
const docs = [...fnDocs, ...lessonDocs.map((d) => ({ ...d, kind: 'lesson' }))];
const top = (q) => rank(q, docs, 3).map((d) => d.id);
assert.equal(top('convert letters to numbers')[0], 'letter-to-number');
assert.equal(top('how do i remove duplicates')[0], 'dedupe');
assert.equal(top('reverse a string')[0], 'reverse-string');
assert.equal(top('days between dates')[0], 'days-between');
assert.equal(top('round to 2 decimals')[0], 'round');
assert.equal(top('ord')[0], 'letter-to-number');
// Every built-in and method has its own entry (tools/reference.py), found by its name or a typo of it.
assert.equal(top('endswith')[0], 'ref-str-endswith');
assert.equal(top('endswit')[0], 'ref-str-endswith');
assert.equal(top('isdigit')[0], 'ref-str-isdigit');
assert.equal(top('zfill')[0], 'ref-str-zfill');
assert.deepEqual(rank('', docs), []);

const notes = noteDocs([{ id: 'n1', title: 'Pre-final', body: 'intro\n## Roman numerals\nuse a dict\n## Hanoi\nrecursion' }]);
assert.deepEqual(notes.map((d) => d.title), ['Pre-final', 'Roman numerals', 'Hanoi']);
assert.equal(rank('roman', notes)[0].href, `notes.html#note=n1&at=${'intro\n'.length}`);

const targets = new Set([...lessons.map((l) => l.id), ...categories.map((c) => `cat-${c.id}`)]);
for (const m of modules) for (const [id] of m.read) assert.ok(targets.has(id), `module ${m.id}: unknown lesson ${id}`);
for (const d of plan.days) for (const [id] of d.read ?? []) assert.ok(targets.has(id), `plan: unknown lesson ${id}`);
for (const r of recipes) assert.ok(r.output !== undefined && r.code, `recipe ${r.id} incomplete`);
console.log('search and learn links ok');

// Helper's "Replace function": swaps one function by name, keeps everything around it.
const { replaceFunction, functionName } = await import('../js/pyblocks.js');
const src = 'import math\n\ndef area(r):\n    return 3 * r\n\n\ndef main():\n    print(area(2))\n\nmain()\n';
assert.equal(replaceFunction(src, 'def area(r):\n    return math.pi * r ** 2\n'),
  'import math\n\ndef area(r):\n    return math.pi * r ** 2\n\n\ndef main():\n    print(area(2))\n\nmain()\n');
assert.equal(replaceFunction(src, 'def missing():\n    pass'), null);
assert.equal(functionName('  def is_prime(n):'), 'is_prime');
const nested = 'class A:\n    def f(self):\n        return 1\n    def g(self):\n        return 2\n';
assert.equal(replaceFunction(nested, 'def f(self):\n    return 10'), 'class A:\n    def f(self):\n        return 10\n    def g(self):\n        return 2\n');
console.log('replace function ok');
