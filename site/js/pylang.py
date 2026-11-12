"""Editor language tools, run inside the page's Pyodide (js/pyworker.js): error checking, completions, call hints."""
import ast
import json

import jedi

try:
    from pyflakes import checker
except ImportError:  # pyflakes comes from PyPI; without it we still report syntax errors
    checker = None

MAX_COMPLETIONS = 60


def lint(code):
    """Return [{line, col, endLine, endCol, message, severity}] with 0-based lines and columns."""
    try:
        compile(code, "<exec>", "exec", dont_inherit=True)
    except SyntaxError as e:
        line = (e.lineno or 1) - 1
        col = max((e.offset or 1) - 1, 0)
        end_line = (e.end_lineno or e.lineno or 1) - 1
        end_col = (e.end_offset or 0) - 1
        if (end_line, end_col) <= (line, col):
            end_line, end_col = line, col + 1
        return json.dumps([{
            "line": line, "col": col, "endLine": end_line, "endCol": end_col,
            "message": f"{type(e).__name__}: {e.msg}", "severity": "error",
        }])
    except (ValueError, RecursionError, MemoryError) as e:  # e.g. null bytes, absurd nesting
        return json.dumps([{"line": 0, "col": 0, "endLine": 0, "endCol": 1,
                            "message": str(e), "severity": "error"}])
    if checker is None:
        return "[]"
    found = []
    for m in sorted(checker.Checker(ast.parse(code), "<exec>").messages, key=lambda m: (m.lineno, m.col)):
        found.append({
            "line": m.lineno - 1, "col": m.col, "endLine": None, "endCol": None,
            "message": m.message % m.message_args,
            # Undefined names crash at run time; the rest (unused import etc.) are advice.
            "severity": "error" if type(m).__name__.startswith("Undefined") else "warning",
        })
    return json.dumps(found)


def complete(code, line, col):
    """line is 1-based, col 0-based (jedi's convention)."""
    try:
        out = []
        for c in jedi.Script(code).complete(line, col):
            out.append({"text": c.name, "kind": c.type, "prefix": c.get_completion_prefix_length()})
            if len(out) == MAX_COMPLETIONS:
                break
        return json.dumps(out)
    except Exception:  # jedi can trip on half-typed code; no completions is fine
        return "[]"


def signature(code, line, col):
    try:
        sigs = jedi.Script(code).get_signatures(line, col)
        if not sigs:
            return "null"
        s = sigs[0]
        return json.dumps({"name": s.name, "params": [p.to_string() for p in s.params], "index": s.index})
    except Exception:
        return "null"
