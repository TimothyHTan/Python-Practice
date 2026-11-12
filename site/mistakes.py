"""Sorts one failed run into a kind of mistake: specific enough to learn from, grouped so the counts add up.

Runs in two places from this one file: the practice page's Pyodide (js/pyworker.js, instant feedback under the
results) and notes_store.py (the Progress page's "Mistakes you make", rebuilt from mistakes.jsonl on every sync,
so improving this file re-sorts old mistakes too). Standard library only.
"""
import ast
import difflib
import json
import re

GROUPS = {
    "syntax": "Code won't run",
    "names": "Names & typos",
    "types": "Text vs numbers",
    "indexes": "Lists, strings & keys",
    "loops": "Loops",
    "output": "Output format",
    "logic": "Logic",
}

# kind -> (group, title, how to avoid it)
KINDS = {
    "missing-colon": ("syntax", "Missing colon", "Lines starting with if, elif, else, for, while and def end with a colon :"),
    "unclosed": ("syntax", "Unclosed bracket or quote", "Every ( [ { and quote needs its partner. The error often points at the line after the real problem."),
    "indentation": ("syntax", "Wrong indentation", "Lines inside an if / for / def are indented 4 spaces; the line after the block goes back out."),
    "assign-vs-compare": ("syntax", "= instead of ==", "= stores a value, == compares two values. Conditions use ==."),
    "syntax-other": ("syntax", "Other syntax error", "Read the line the error points at and the line just before it."),
    "typo": ("names", "Misspelled name", "Python is case-sensitive and spelling-exact. Copy a name instead of retyping it."),
    "used-before-set": ("names", "Used a variable before giving it a value", "Give a variable its starting value (like total = 0) above the line that uses it."),
    "undefined-name": ("names", "Name that was never created", "Either it's text and needs quotes, or the variable was never created."),
    "wrong-method": ("names", "Method that type doesn't have", "Text has .upper(), .split(), .strip(); lists have .append(), .sort(). Check what type the value is."),
    "forgot-int": ("types", "Forgot int() on the input", "input() always gives text. Use int(input()) or float(input()) before doing maths."),
    "text-plus-number": ("types", "Joined text and a number with +", "Use print('Total:', total) or an f-string: f'Total: {total}'."),
    "bad-int": ("types", "int() on text that isn't a number", "int() only takes a whole number like '42'. Split the line first; use float() for decimals."),
    "none-value": ("types", "Used None as a value", ".sort(), .append() and print() give back None. A function without return also gives None."),
    "type-other": ("types", "Wrong type of value", "Read the last line of the error: it names the types that didn't fit together."),
    "index-range": ("indexes", "Index past the end", "Indexes go from 0 to len(x) - 1. The last item is x[-1]."),
    "missing-key": ("indexes", "Dictionary key that isn't there", "Check with `if key in d:` or use d.get(key, 0)."),
    "infinite-loop": ("loops", "Loop that never ends", "Something inside a while loop must change the thing its condition checks."),
    "print-in-loop": ("loops", "Printed inside the loop", "To print only the final answer, un-indent print so it runs once, after the loop."),
    "off-by-one": ("loops", "Off by one", "range(a, b) stops before b. Check < vs <= and where the count starts."),
    "not-iterable": ("loops", "Looped over a number", "for i in range(n) repeats n times; you can't loop over n itself."),
    "no-output": ("output", "Printed nothing", "The answer has to be printed. A function does nothing until you call it, and return doesn't print."),
    "input-prompt": ("output", "Text inside input()", "The checker types the input for you. input('Enter: ') prints 'Enter: ' too, so use plain input()."),
    "spacing": ("output", "Spaces or blank lines", "print(a, b) puts a space between. Use sep='' or an f-string when there shouldn't be one."),
    "capitals": ("output", "Capital letters", "Match the expected output's capitals exactly; .upper(), .lower(), .title() help."),
    "punctuation": ("output", "Punctuation or symbols", "Copy the exact text from the expected output, commas and colons included."),
    "number-format": ("output", "Number format", "/ always gives a decimal (6 / 2 is 3.0). Use // for whole numbers, round(x, 2) or f'{x:.2f}' for decimals."),
    "extra-output": ("output", "Printed extra lines", "Remove test prints. Print only what the problem asks for."),
    "missing-lines": ("output", "Part of the answer missing", "Compare with the expected output line by line: something isn't printed."),
    "wrong-variable": ("logic", "Printed the wrong variable", "Ask: which variable holds the answer? Print that one."),
    "unused-input": ("logic", "Read the input but never used it", "Every input you read is there for a reason: the answer should depend on it."),
    "extra-input": ("logic", "Read more input lines than there are", "Each input() reads one whole line. If the values share a line, read it once and .split() it."),
    "div-zero": ("logic", "Divided by zero", "Check the number you divide by isn't 0 first (e.g. an empty list's length)."),
    "recursion": ("logic", "Function calls itself forever", "A recursive function needs a base case that returns without calling itself."),
    "error-other": ("logic", "Other error", "Read the last line of the error, then the line it points at."),
    "wrong-answer": ("logic", "Wrong answer", "Trace your code by hand with the sample input, writing each variable's value after every line."),
}

# kind -> (Learn page anchor, what to revise there). tools/build_learn.py checks every anchor exists.
LEARN = {
    "missing-colon": ("l3-lesson", "Level 3: blocks end with a colon"),
    "unclosed": ("errors", "Level 7: Error field guide"),
    "indentation": ("l3-lesson", "Level 3: indentation shows what's inside a block"),
    "assign-vs-compare": ("level-1-operators", "Level 1: = stores, == compares"),
    "syntax-other": ("errors", "Level 7: Error field guide"),
    "typo": ("errors", "Level 7: Error field guide"),
    "used-before-set": ("l3-together", "Level 3: start the counter before the loop"),
    "undefined-name": ("l1-lesson", "Level 1: variables and text in quotes"),
    "wrong-method": ("l2-lesson", "Level 2: string methods"),
    "forgot-int": ("level-1-converting-between-types", "Level 1: converting input to numbers"),
    "text-plus-number": ("level-1-putting-values-into-text", "Level 1: putting values into text"),
    "bad-int": ("l2-together", "Level 2: splitting a line before int()"),
    "none-value": ("l4-mistakes", "Level 4: saving the result of .sort()"),
    "type-other": ("errors", "Level 7: Error field guide"),
    "index-range": ("l4-mistakes", "Level 4: reaching one past the end"),
    "missing-key": ("level-5-dictionaries", "Level 5: .get() with a default"),
    "infinite-loop": ("l3-mistakes", "Level 3: a while loop that never ends"),
    "print-in-loop": ("l3-together", "Level 3: print after the loop"),
    "off-by-one": ("level-3-loops", "Level 3: where range() stops"),
    "not-iterable": ("level-3-loops", "Level 3: for loops and range()"),
    "no-output": ("l6-together", "Level 6: return vs print"),
    "input-prompt": ("l2-together", "Level 2: plain input() on the Practice page"),
    "spacing": ("level-1-putting-values-into-text", "Level 1: putting values into text"),
    "capitals": ("l2-lesson", "Level 2: .upper(), .lower(), .title()"),
    "punctuation": ("level-1-putting-values-into-text", "Level 1: putting values into text"),
    "number-format": ("level-1-putting-values-into-text", "Level 1: :.2f and // vs /"),
    "extra-output": ("l1-lesson", "Level 1: print()"),
    "missing-lines": ("l1-lesson", "Level 1: print()"),
    "wrong-variable": ("l3-together", "Level 3: print the counter, not the loop variable"),
    "unused-input": ("l2-together", "Level 2: using the text from input()"),
    "extra-input": ("l3-input", "Level 3: loops that read input"),
    "div-zero": ("l4-project", "Level 4: check for an empty list first"),
    "recursion": ("l6-lesson", "Level 6: functions"),
    "error-other": ("tracebacks", "Level 7: reading a traceback"),
    "wrong-answer": ("ooda", "Level 7: the debugging loop"),
}

LOOPS = (ast.For, ast.While)


def _norm(s):
    """Same rules as js/grade.js: Windows line endings, trailing spaces and trailing blank lines don't count."""
    return re.sub(r"\n+$", "", "\n".join(line.rstrip() for line in (s or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")))


def _num(s):
    try:
        return float(s)
    except ValueError:
        return None


def _result(kind, detail="", line=None):
    group, title, tip = KINDS[kind]
    learn, learn_label = LEARN[kind]
    return {"group": group, "groupTitle": GROUPS[group], "kind": kind, "title": title, "detail": detail, "tip": tip, "line": line,
            "learn": learn, "learnLabel": learn_label}


def _syntax(e):
    msg = e.msg or ""
    if isinstance(e, (IndentationError, TabError)):
        kind = "indentation"
    elif "expected ':'" in msg:
        kind = "missing-colon"
    elif "'=='" in msg or "instead of '='" in msg:
        kind = "assign-vs-compare"
    elif any(s in msg for s in ("never closed", "unterminated", "unmatched", "does not match opening", "EOF")):
        kind = "unclosed"
    else:
        kind = "syntax-other"
    return _result(kind, f"Line {e.lineno}: {type(e).__name__}: {msg}", e.lineno)


class _Facts:
    """What the code does, from its syntax tree."""

    def __init__(self, tree):
        self.stored, self.loaded, self.loop_vars = {}, set(), set()  # stored: name -> (first line, node assigned)
        self.prints, self.prints_in_loop, self.prompts, self.calls = [], False, [], set()
        self.defs = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.has_loop = any(isinstance(n, LOOPS) for n in ast.walk(tree))
        self.has_return = any(isinstance(n, ast.Return) for n in ast.walk(tree))
        self._visit(tree, None)

    def _visit(self, node, loop):
        if isinstance(node, ast.For):
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    self.loop_vars.add(n.id)
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load):
                self.loaded.add(node.id)
            elif node.id not in self.loop_vars:
                self.stored.setdefault(node.id, (node.lineno, None))
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    self.stored.setdefault(t.id, (node.lineno, node.value))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            self.calls.add(node.func.id)
            if node.func.id == "print":
                # loop is the loop this print sits in, if any; prints inside a def run wherever it's called
                self.prints.append((node, loop))
                self.prints_in_loop |= loop is not None
            if node.func.id == "input" and node.args and isinstance(node.args[0], ast.Constant) and str(node.args[0].value).strip():
                self.prompts.append((str(node.args[0].value), node.lineno))
        for child in ast.iter_child_nodes(node):
            inner = node if isinstance(node, LOOPS) and child not in (getattr(node, "iter", None), getattr(node, "target", None)) else loop
            self._visit(child, None if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else inner)

    def unused(self):
        """Variables that get a value but are never read: [(name, line, assigned from input()?)]."""
        out = []
        for name, (line, value) in self.stored.items():
            if name in self.loaded or name.startswith("_") or name in self.loop_vars:
                continue
            from_input = value is not None and any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "input" for n in ast.walk(value))
            out.append((name, line, from_input))
        return sorted(out, key=lambda x: x[1])

    def loop_var_printed_after_loop(self):
        """(name, line) of a print outside any loop whose argument is a for-loop variable."""
        for call, loop in self.prints:
            if loop is None:
                for arg in call.args:
                    if isinstance(arg, ast.Name) and arg.id in self.loop_vars:
                        return arg.id, call.lineno
        return None


def _error(code, err, facts, input_text):
    """Mistake from a run-time error message (the traceback's last line)."""
    lines = [l for l in err.strip().splitlines() if l.strip()]
    last = lines[-1] if lines else ""
    nums = re.findall(r'File "<exec>", line (\d+)', err)
    line = int(nums[-1]) if nums else None
    name, _, msg = last.partition(":")
    name, msg = name.strip().split(".")[-1], msg.strip()
    where = f"Line {line}: " if line else ""
    if name in ("NameError", "UnboundLocalError"):
        m = re.search(r"'(\w+)'", msg)
        bad = m.group(1) if m else "?"
        if facts and bad in facts.stored and line and facts.stored[bad][0] > line:
            return _result("used-before-set", f"{where}`{bad}` is used here but only gets a value on line {facts.stored[bad][0]}.", line)
        if name == "UnboundLocalError" or "before assignment" in msg:
            return _result("used-before-set", f"{where}{msg}", line)
        known = sorted((facts.stored.keys() | facts.loop_vars | facts.defs) if facts else set()) + ["print", "input", "int", "float", "str", "len", "range", "True", "False", "None"]
        near = re.search(r"Did you mean: '(\w+)'", msg)
        near = near.group(1) if near else next(iter(difflib.get_close_matches(bad, known, 1, 0.7)), None)
        if near:
            return _result("typo", f"{where}you wrote `{bad}`, probably meaning `{near}`.", line)
        return _result("undefined-name", f"{where}`{bad}` doesn't exist. If it's text, it needs quotes: '{bad}'.", line)
    if name == "AttributeError":
        if "NoneType" in msg:
            return _result("none-value", f"{where}{msg}", line)
        return _result("wrong-method", f"{where}{msg}", line)
    if name == "TypeError":
        if "NoneType" in msg:
            return _result("none-value", f"{where}{msg}", line)
        if re.search(r"'(int|float)' object is not iterable", msg):
            return _result("not-iterable", f"{where}{msg}. Did you mean range(...)?", line)
        if "can only concatenate str" in msg or re.search(r"unsupported operand.*'str'|'str' and '(int|float)'|'(int|float)' and 'str'|not supported between instances of '(str|int|float)' and '(str|int|float)'", msg):
            src_line = code.splitlines()[line - 1] if line and line <= len(code.splitlines()) else ""
            if "can only concatenate str" in msg and re.search(r"""["'].*["']\s*\+|\+\s*["']""", src_line):
                return _result("text-plus-number", f"{where}{msg}.", line)
            return _result("forgot-int", f"{where}{msg}. The value from input() is still text.", line)
        return _result("type-other", f"{where}{msg}", line)
    if name == "ValueError" and "invalid literal" in msg:
        m = re.search(r"'(.*)'$", msg)
        text = m.group(1) if m else ""
        why = " It has spaces: split it first." if " " in text.strip() else " Use float() for decimals." if re.fullmatch(r"-?\d*\.\d+", text) else ""
        return _result("bad-int", f"{where}{msg}.{why}", line)
    if name == "IndexError":
        return _result("index-range", f"{where}{msg}", line)
    if name == "KeyError":
        return _result("missing-key", f"{where}the key {msg} isn't in the dictionary.", line)
    if name == "ZeroDivisionError":
        return _result("div-zero", f"{where}{msg}", line)
    if name == "RecursionError":
        return _result("recursion", f"{where}{msg}", line)
    if name == "EOFError":
        lines_in = len((input_text or "").splitlines())
        return _result("extra-input", f"{where}input() ran again, but the input only has {lines_in} line{'' if lines_in == 1 else 's'}.", line)
    return _result("error-other", f"{where}{last}", line)


def _wrong_output(code, facts, input_text, expected, got):
    exp, out = _norm(expected), _norm(got)
    el, gl = exp.split("\n"), out.split("\n")
    show = lambda s: s if len(s) <= 40 else s[:37] + "..."
    if not out.strip():
        if facts:
            never = sorted(facts.defs - facts.calls)
            if never:
                return _result("no-output", f"`{never[0]}()` is defined but never called.")
            if not facts.prints and facts.has_return:
                return _result("no-output", "The function returns the answer, but nothing prints it.")
            if not facts.prints:
                return _result("no-output", "There's no print() in the code.")
        return _result("no-output", "The program finished without printing anything.")
    if facts:
        for prompt, line in facts.prompts:
            if prompt.strip() in out:
                return _result("input-prompt", f"Line {line}: input('{show(prompt)}') printed '{show(prompt.strip())}' into your output.", line)
    tokens = (input_text or "").split()
    if len(tokens) > 1 and all(_num(t) is not None for t in tokens) and out.strip() == "".join(tokens):
        return _result("forgot-int", f"Your output {show(out.strip())} is the inputs glued together like text, not added as numbers.")
    if re.sub(r"\s+", "", exp) == re.sub(r"\s+", "", out):
        return _result("spacing", f"Right characters, different spacing: expected '{show(el[0])}', got '{show(gl[0])}'.")
    if exp.lower() == out.lower():
        return _result("capitals", f"Only capital letters differ: expected '{show(exp)}', got '{show(out)}'.")
    if re.sub(r"[\W_]+", "", exp.lower()) == re.sub(r"[\W_]+", "", out.lower()):
        return _result("punctuation", f"Only punctuation or symbols differ: expected '{show(exp)}', got '{show(out)}'.")
    if len(el) == len(gl):
        pairs = [(_num(a), _num(b)) for a, b in zip(el, gl) if a != b]
        if pairs and all(a is not None and b is not None and abs(a - b) < 0.01 for a, b in pairs):
            a, b = next((x, y) for x, y in zip(el, gl) if x != y)
            return _result("number-format", f"Same number, written differently: expected {a}, got {b}.")
    if facts:
        bad = facts.loop_var_printed_after_loop()
        unused = [u for u in facts.unused() if not u[2]]
        printed = [(a.id, call.lineno) for call, _ in facts.prints for a in call.args if isinstance(a, ast.Name)]
        if unused and printed:
            name, line, _ = unused[0]
            # mark the print line: that's where the fix goes
            return _result("wrong-variable", f"`{name}` gets a value on line {line} but is never used, and you print `{printed[0][0]}`.", printed[0][1])
        if bad:
            return _result("wrong-variable", f"Line {bad[1]}: after the loop, `{bad[0]}` only holds the last item it looped over.", bad[1])
        ignored = [u for u in facts.unused() if u[2]]
        if ignored:
            return _result("unused-input", f"`{ignored[0][0]}` is read on line {ignored[0][1]} but never used.", ignored[0][1])
        loop_print = next((c.lineno for c, loop in facts.prints if loop is not None), None)
        if len(el) == 1 and len(gl) > 1 and loop_print:
            return _result("print-in-loop", f"Line {loop_print}: print runs on every pass of the loop, giving {len(gl)} lines instead of 1.", loop_print)
    if len(el) == len(gl) and facts and facts.has_loop:
        diffs = [(_num(a), _num(b)) for a, b in zip(el, gl) if a != b]
        if diffs and all(a is not None and b is not None and abs(a - b) == 1 for a, b in diffs):
            return _result("off-by-one", f"Your numbers are 1 away from the expected ones (expected {show(el[0])}, got {show(gl[0])}).")
    if abs(len(el) - len(gl)) == 1 and facts and facts.has_loop:
        longer, shorter = (gl, el) if len(gl) > len(el) else (el, gl)
        if longer[1:] == shorter or longer[:-1] == shorter:
            how = "one time too many" if len(gl) > len(el) else "one time too few"
            return _result("off-by-one", f"The loop runs {how}: {len(gl)} lines instead of {len(el)}.")
    if len(gl) > len(el) and all(line in gl for line in el):
        extra = next(line for line in gl if line not in el)
        return _result("extra-output", f"Your output has lines the expected one doesn't, like '{show(extra)}'.")
    if len(gl) < len(el) and all(line in el for line in gl):
        missing = next(line for line in el if line not in gl)
        return _result("missing-lines", f"Missing the line '{show(missing)}'.")
    return _result("wrong-answer", f"Expected '{show(el[0])}'{' …' if len(el) > 1 else ''}, got '{show(gl[0])}'{' …' if len(gl) > 1 else ''}.")


def classify(code, input="", expected="", got="", error="", timeout=False):
    """One failed run -> {group, groupTitle, kind, title, detail, tip, line}. line is 1-based or None."""
    try:
        facts = _Facts(ast.parse(code or ""))
    except SyntaxError as e:
        return _syntax(e)
    except (ValueError, RecursionError, MemoryError):
        facts = None
    if timeout:
        line = next((n.lineno for n in ast.walk(ast.parse(code)) if isinstance(n, ast.While)), None) if facts else None
        return _result("infinite-loop", f"Line {line}: this loop never stopped within the time limit." if line else "The program never finished within the time limit.", line)
    if error:
        return _error(code or "", error, facts, input)
    return _wrong_output(code or "", facts, input, expected, got)


def classify_json(payload):
    """For js/pyworker.js: JSON in, JSON out."""
    p = json.loads(payload)
    return json.dumps(classify(p.get("code", ""), p.get("input", ""), p.get("expected", ""), p.get("got", ""), p.get("error", ""), bool(p.get("timeout"))))


if __name__ == "__main__":
    def k(*a, **kw):
        return classify(*a, **kw)["kind"]
    vowels = 'sentence = input()\nvowels = "aeiou"\nz = 0\nfor x in sentence:\n    for y in vowels:\n        if x == y:\n            z += 1\n\nprint(x)\n'
    r = classify(vowels, "Hello, world!", "3", "!")
    assert r["kind"] == "wrong-variable" and "`z`" in r["detail"] and r["line"] == 9, r
    assert k(vowels.replace("print(x)", "print(z)").replace("z += 1", "z += 1\n            print(z)"), "Hello, world!", "3", "1\n2\n3") == "print-in-loop"
    assert k("if x == 1\n    print(1)") == "missing-colon"
    assert k("print('hi'") == "unclosed"
    assert k("for i in range(3):\nprint(i)") == "indentation"
    assert k("x = 1\nif x = 1:\n    print(x)") == "assign-vs-compare"
    assert k("total = 0\nprint(totl)", error='File "<exec>", line 2\nNameError: name \'totl\' is not defined') == "typo"
    assert k("print(hello)", error="NameError: name 'hello' is not defined") == "undefined-name"
    assert k("print(n)\nn = 5", error='File "<exec>", line 1\nNameError: name \'n\' is not defined') == "used-before-set"
    assert k("n = input()\nprint(n + 1)", error='File "<exec>", line 2\nTypeError: can only concatenate str (not "int") to str') == "forgot-int"
    assert k("n = 5\nprint('n is ' + n)", error='File "<exec>", line 2\nTypeError: can only concatenate str (not "int") to str') == "text-plus-number"
    assert k("a = input()\nb = input()\nprint(a + b)", "2\n3", "5", "23") == "forgot-int"
    assert "split" in classify("n = int(input())", error="ValueError: invalid literal for int() with base 10: '3 4'")["detail"]
    assert k("x = [1]\nprint(x[1])", error="IndexError: list index out of range") == "index-range"
    assert k("while True:\n    pass", timeout=True) == "infinite-loop"
    r = classify("a = input()\nb = input()", "2 3", error='File "<exec>", line 2\nEOFError: EOF when reading a line')
    assert r["kind"] == "extra-input" and "only has 1 line" in r["detail"], r
    assert k("print('hi')", "", "hi", "") == "no-output"
    assert k("def f():\n    print(1)", "", "1", "") == "no-output"
    assert k("n = input('Number: ')\nprint(n)", "4", "4", "Number: 4") == "input-prompt"
    assert k("print('a','b')", "", "ab", "a b") == "spacing"
    assert k("print('hello')", "", "Hello", "hello") == "capitals"
    assert k("print(6/2)", "", "3", "3.0") == "number-format"
    assert k("for i in range(4):\n    print(4 - i)", "", "3\n2\n1", "4\n3\n2\n1") == "off-by-one"
    assert k("n = int(input())\nprint(5)", "3", "6", "5") == "unused-input"
    assert k("print(1)\nprint(2)", "", "2", "1\n2") == "extra-output"
    assert k("print(7)", "", "8", "9") == "wrong-answer"  # 1 away, but no loop to blame
    assert k("n = 0\nfor i in range(4):\n    n += 1\nprint(n)", "", "3", "4") == "off-by-one"
    assert all(g in GROUPS for g, _, _ in KINDS.values())
    assert KINDS.keys() == LEARN.keys(), set(KINDS) ^ set(LEARN)
    assert json.loads(classify_json(json.dumps({"code": "print(", "error": "x"})))["group"] == "syntax"
    print("mistakes self-check passed")
