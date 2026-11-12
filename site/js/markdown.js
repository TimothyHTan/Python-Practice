// Notes are markdown. Rendered with marked; raw HTML inside a note is shown as text, and Python code blocks
// are highlighted like the rest of the site. Pages load this lazily, so search and editing work without it.
import { Marked } from 'https://cdn.jsdelivr.net/npm/marked@15.0.12/lib/marked.esm.js';
import { highlight } from './palette.js?v=5';

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

const md = new Marked({
  gfm: true,
  breaks: true, // a new line in a note is a new line on screen, like in the editor
  renderer: {
    html: ({ text }) => esc(text),
    code: ({ text, lang }) => `<pre class="cm-s-vw code-view"><code>${!lang || /^py(thon)?3?$/i.test(lang) ? highlight(text) : esc(text)}</code></pre>`,
  },
});

export const renderMarkdown = (text) => md.parse(text ?? '');

// The note's top-level blocks, each with its offset in the text, so a click on the rendered note can open the
// editor at the same place, and a search hit can scroll the rendered note to it.
export function markdownBlocks(text) {
  const tokens = md.lexer(text ?? '');
  const out = [];
  let at = 0;
  for (const t of tokens) {
    if (t.type !== 'space') out.push({ at, html: md.parser(Object.assign([t], { links: tokens.links })) });
    at += t.raw.length;
  }
  return out;
}
