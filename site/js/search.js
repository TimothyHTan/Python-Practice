// Plain-English search over functions, lessons, problems and notes. No DOM here, so node can test it.
// A doc is { kind, title, where, keys, code, text, href }.

const STOP = new Set(('a an the to of in on for from into how do does did i im my me can could you your is are be it its '
  + 'with and or what which way get make using use by as at this that want need some python then out up so like').split(' '));

// Words people type -> words the docs use. Every word in a group finds the others.
const GROUPS = [
  'letter char character alphabet', 'number int integer digit num numeric', 'convert turn change cast transform parse',
  'text string str', 'list array', 'dict dictionary map mapping', 'remove delete drop', 'duplicate unique distinct dedupe',
  'find search locate position', 'count tally frequency many', 'reverse backward flip', 'sort order arrange',
  'error exception crash', 'decimal float', 'biggest largest max maximum highest', 'smallest min minimum lowest',
  'average mean', 'capital uppercase upper', 'lowercase lower small', 'loop iterate repeat', 'join combine glue concatenate',
  'split separate', 'print output show display', 'round rounding', 'file txt', 'empty blank', 'add append insert',
  'check test validate', 'space whitespace trim strip',
].map((g) => g.split(' '));

export function norm(word) {
  word = word.toLowerCase();
  return word.length > 3 && word.endsWith('s') && !word.endsWith('ss') ? word.slice(0, -1) : word;
}

export const tokens = (s) => (s ?? '').toLowerCase().match(/[a-z0-9_]+/g)?.map(norm) ?? [];

const synonyms = new Map();
for (const g of GROUPS) for (const w of g) synonyms.set(norm(w), g.map(norm).filter((x) => x !== norm(w)));

export function queryTokens(q) {
  const all = tokens(q);
  const kept = all.filter((t) => !STOP.has(t));
  return kept.length ? kept : all;
}

const FIELDS = [['title', 4], ['keys', 3], ['where', 2], ['code', 2], ['text', 1]];
const cache = new WeakMap();

function fieldsOf(doc) {
  let f = cache.get(doc);
  if (!f) cache.set(doc, (f = FIELDS.map(([name, weight]) => [tokens(doc[name]), weight])));
  return f;
}

// Best weight with which one query word appears in the doc. Prefix match lets "conv" find "convert".
function hit(fields, word) {
  const alts = [[word, 1], ...(synonyms.get(word) ?? []).map((s) => [s, 0.8])];
  let best = 0;
  for (const [list, weight] of fields) {
    if (weight <= best) continue;
    for (const [w, factor] of alts) {
      if (list.some((t) => t === w || (w.length > 1 && t.startsWith(w)))) { best = Math.max(best, weight * factor); break; }
    }
  }
  return best;
}

const BOOST = { fn: 1.5, lesson: 0.5, problem: 0, note: 0.5 };

export function rank(query, docs, limit = 40) {
  const words = queryTokens(query);
  if (!words.length) return [];
  const need = Math.max(1, Math.ceil(words.length * 0.67));
  const phrase = query.trim().toLowerCase();
  const scored = [];
  for (const doc of docs) {
    const fields = fieldsOf(doc);
    let score = 0, matched = 0;
    for (const w of words) {
      const s = hit(fields, w);
      if (s) { score += s; matched++; }
    }
    if (matched < need) continue;
    if (phrase.length > 2 && doc.title.toLowerCase().includes(phrase)) score += 4;
    scored.push({ doc, matched, score: score + (BOOST[doc.kind] ?? 0) });
  }
  scored.sort((a, b) => b.matched - a.matched || b.score - a.score);
  return scored.slice(0, limit).map((s) => s.doc);
}

// Notes: one search entry per markdown heading section (or paragraph when there are no headings).
export function noteDocs(notes) {
  const docs = [];
  for (const note of notes) {
    const body = note.body ?? '';
    const heads = [...body.matchAll(/^#{1,6}\s+(.*)$/gm)];
    const parts = heads.length
      ? [{ at: 0, title: note.title }, ...heads.map((m) => ({ at: m.index, title: m[1] }))]
      : [...body.matchAll(/[^\n][\s\S]*?(?=\n\s*\n|$)/g)].map((m) => ({ at: m.index, title: m[0].split('\n')[0] }));
    parts.forEach((p, i) => {
      const text = body.slice(p.at, parts[i + 1]?.at ?? body.length).trim();
      if (!text && i) return;
      docs.push({
        kind: 'note', title: (p.title || note.title || 'Untitled note').slice(0, 90), where: `Note · ${note.title || 'Untitled note'}`,
        keys: note.title, code: '', text: text.slice(0, 1500), href: `notes.html#note=${note.id}&at=${p.at}`,
      });
    });
  }
  return docs;
}
