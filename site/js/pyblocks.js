// Find and replace a Python function in source text, by name. Used by the helper's "Replace function" button.

const indentOf = (line) => line.match(/^\s*/)[0].length;

// Lines [start, end) of `def name(...)` and its body, or null. Trailing blank lines are left outside.
export function findFunction(src, name) {
  const lines = src.split('\n');
  const head = new RegExp(`^\\s*def\\s+${name}\\s*\\(`);
  const start = lines.findIndex((l) => head.test(l));
  if (start < 0) return null;
  const indent = indentOf(lines[start]);
  let end = start + 1;
  while (end < lines.length && (lines[end].trim() === '' || indentOf(lines[end]) > indent)) end++;
  while (end > start + 1 && lines[end - 1].trim() === '') end--;
  return { start, end, indent };
}

// The name of the first function defined in a snippet, or null.
export const functionName = (code) => code.match(/^\s*def\s+(\w+)\s*\(/m)?.[1] ?? null;

// src with the snippet's function swapped in (re-indented to match), or null if src doesn't have it.
export function replaceFunction(src, code) {
  const name = functionName(code);
  const at = name && findFunction(src, name);
  if (!at) return null;
  const snippet = code.replace(/\s+$/, '').split('\n');
  const strip = Math.min(...snippet.filter((l) => l.trim()).map(indentOf));
  const pad = ' '.repeat(at.indent);
  const fresh = snippet.map((l) => (l.trim() ? pad + l.slice(strip) : ''));
  const lines = src.split('\n');
  return [...lines.slice(0, at.start), ...fresh, ...lines.slice(at.end)].join('\n');
}
