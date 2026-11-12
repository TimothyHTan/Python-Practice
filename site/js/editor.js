// Python editor: CodeMirror 5 plus error checking, completions and call hints from the page's Python (js/python.js).
import { tool, on, status } from './python.js?v=6';
const { Pos } = CodeMirror;

/* Language tools. One request runs at a time; a newer request of the same type replaces a waiting one. */
let busy = false;
const waiting = new Map(); // type -> { payload, resolve }

function ask(type, payload) {
  if (!status.tools) return Promise.resolve(null);
  return new Promise((resolve) => {
    waiting.get(type)?.resolve(null);
    waiting.set(type, { payload, resolve });
    pump();
  });
}
function pump() {
  if (busy || !waiting.size) return;
  const [type, job] = waiting.entries().next().value;
  waiting.delete(type);
  busy = true;
  tool(type, job.payload).then((result) => { busy = false; job.resolve(result); pump(); });
}

/* Red and yellow underlines */
function lint(text, done, _options, cm) {
  ask('lint', { code: text }).then((found) => done((found ?? []).map((f) => {
    let from = Pos(f.line, f.col);
    let to = f.endLine == null ? null : Pos(f.endLine, f.endCol);
    if (!to) ({ anchor: from, head: to } = cm.findWordAt(from));
    // An error past the end of a line has nothing to underline, so mark the last character.
    const len = cm.getLine(from.line)?.length ?? 0;
    if (from.ch >= len && to.line === from.line) { from = Pos(from.line, Math.max(len - 1, 0)); to = Pos(from.line, len); }
    return { from, to, message: f.message, severity: f.severity };
  })));
}

/* Completions */
function hint(cm, done) {
  const cur = cm.getCursor();
  if (!status.tools) return done(CodeMirror.hint.anyword(cm)); // words already in the file, until Python has loaded
  ask('complete', { code: cm.getValue(), line: cur.line + 1, col: cur.ch }).then((items) => {
    if (!items?.length) return done(null);
    const from = Pos(cur.line, cur.ch - items[0].prefix);
    if (items.length === 1 && items[0].text === cm.getRange(from, cur)) return done(null); // already typed
    done({
      from, to: cur,
      list: items.map((item) => ({
        text: item.text,
        render(el) {
          el.textContent = item.text;
          const kind = el.appendChild(document.createElement('span'));
          kind.className = 'hint-kind';
          kind.textContent = item.kind;
        },
      })),
    });
  });
}
hint.async = true;

/* Call hint: shows a function's parameters while the cursor is inside its brackets */
const tip = document.body.appendChild(document.createElement('div'));
tip.className = 'sig-tip';
tip.hidden = true;
let tipTimer;
function updateTip(cm) {
  clearTimeout(tipTimer);
  tipTimer = setTimeout(async () => {
    const cur = cm.getCursor();
    const sig = cm.hasFocus() && !cm.somethingSelected()
      ? await ask('signature', { code: cm.getValue(), line: cur.line + 1, col: cur.ch }) : null;
    if (!sig || !cm.hasFocus()) { tip.hidden = true; return; }
    tip.replaceChildren(`${sig.name}(`, ...sig.params.flatMap((p, i) => {
      const el = document.createElement(i === sig.index ? 'strong' : 'span');
      el.textContent = p;
      return i ? [', ', el] : [el];
    }), ')');
    tip.hidden = false;
    const at = cm.cursorCoords(cur, 'window');
    tip.style.left = `${Math.max(8, Math.min(at.left, innerWidth - tip.offsetWidth - 8))}px`;
    const above = at.top - tip.offsetHeight - 6;
    tip.style.top = `${above < 4 ? at.bottom + 6 : above}px`;
  }, 150);
}

export function createEditor(textarea, onRun, onLint) {
  const cm = CodeMirror.fromTextArea(textarea, {
    mode: 'python', theme: 'vw', keyMap: 'sublime',
    lineNumbers: true, indentUnit: 4,
    autoCloseBrackets: true, matchBrackets: true, styleActiveLine: true,
    gutters: ['CodeMirror-lint-markers', 'CodeMirror-linenumbers'],
    lint: { getAnnotations: lint, async: true, delay: 400, onUpdateLinting: (found) => onLint?.(found) },
    hintOptions: { hint, completeSingle: false },
    extraKeys: {
      Tab: (c) => (c.somethingSelected() ? c.indentSelection('add') : c.replaceSelection('    ')),
      'Shift-Tab': 'indentLess',
      'Ctrl-Space': 'autocomplete',
      'Ctrl-Enter': onRun,
      'Alt-Up': 'swapLineUp',
      'Alt-Down': 'swapLineDown',
      'Shift-Alt-Down': 'duplicateLine',
    },
  });

  // Offer completions while typing a name or after a dot, like VS Code.
  cm.on('inputRead', (c, change) => {
    if (c.state.completionActive || !/^[\w.]$/.test(change.text[0])) return;
    const type = c.getTokenAt(c.getCursor()).type;
    if (type !== 'comment' && type !== 'string') c.showHint();
  });
  cm.on('cursorActivity', updateTip);
  cm.on('blur', () => { clearTimeout(tipTimer); tip.hidden = true; });
  cm.on('scroll', () => { tip.hidden = true; });

  on('tools', () => cm.performLint()); // if they never load, the editor keeps working without them
  return cm;
}
