"""Saves practice progress to Documents\\python notes and works out which functions you use.

The browser keeps a working copy in localStorage and sends changes to POST /api/sync (server.py).
See AGENT_MD below (written to the folder as agent.md) for the file layout.
"""
import ast
import csv
import io
import json
import os
import re
import threading
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import mistakes  # site/mistakes.py: sorts a failed run into a kind of mistake

DEFAULT = Path.home() / "Documents" / "python notes"
DATA = DEFAULT  # server.py swaps this for the folder picked on the Settings page
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")  # problem ids; also keeps file names safe
MAX_TEXT = 100_000
LOCK = threading.Lock()
ATTEMPT_FIELDS = ["time", "problem", "mode", "passed", "total"]
FAIL_TEXT = {"code": MAX_TEXT, "input": 20_000, "expected": 20_000, "got": 20_000, "error": 20_000}

AGENT_MD = """# python notes: how this folder works

This folder is written by the Vertical World practice site.
The site runs at http://localhost:8000/site/ (start it with `site\\start.bat` on Windows or `./site/start.sh` on Linux).
Every change you make on the site is saved here about 1.5 seconds later.

## What is stored where

| Path | What it holds | Written when |
|---|---|---|
| `progress.json` | `solvedAt` (problem id -> time last solved, ms since 1970) and `lessonsDone` (Learn levels marked done) | any sync |
| `code/<problem-id>.py` | your latest code for that problem | you type in the editor |
| `pseudocode/<problem-id>.md` | your pseudocode / algorithm plan for that problem | you type in the Pseudocode tab |
| `attempts.csv` | one row per "Run samples" or "Submit": time, problem, mode, passed, total | you run or submit |
| `mistakes.jsonl` | one JSON line per failed run: `t`, `time`, `problem`, `mode`, your `code`, and the first failing case's `input`, `expected`, `got`, `error` (or `timeout`) | a run or submit fails |
| `analytics.json` | computed: which functions and constructs your code uses, attempts per problem, mistakes by kind (sorted by `site/mistakes.py`) | rebuilt on every sync |
| `analytics.md` | the same analytics as readable tables | rebuilt on every sync |
| `agent.md` | this file | created if missing |

Problem ids (like `pf-caesar`) are the `id` fields in `site/js/problems.js`, made by `site/tools/build_problems.py`.

## How syncing works

- The browser's localStorage is the working copy (keys `vw.code.<id>`, `vw.pseudo.<id>`, `vw.solvedAt`, `vw.lessons.done`).
- Each page load sends everything to `POST /api/sync` with `"full": true`. The server merges and
  answers with anything this browser is missing, so a cleared or new browser gets its work back.
- Merge rules: the browser's text wins for code and pseudocode it has; an empty text deletes the file;
  `solvedAt` keeps the later time per problem; `lessonsDone` is the union; attempts are only appended.
- Files are written to a temp file first and then renamed, so a crash never leaves half a file.

## How to update things safely

- **Change code or pseudocode:** do it in the site. Editing `code/*.py` here by hand works only if
  the browser has no copy of that problem, otherwise the browser's copy overwrites yours on the next sync.
- **Reset everything:** stop the server, delete this folder, and clear the site's data in the browser
  (DevTools > Application > Local Storage > delete the `vw.*` keys). Deleting only one side brings it back from the other.
- **Recompute analytics:** they rebuild on every sync; just open the site's Progress page.
- **Add a new field:** add it to `notes_store.py` (`sync()` merge and `analyze()`), send it from
  `site/js/sync.js`, and document it in the table above. Keep `progress.json` small; put anything per-problem in its own file.
- **Move the folder:** use the site's Settings page; it copies this folder's contents to the new place.
"""


def _write(path: Path, text: str):
    """Atomic write: never leaves a half-written file behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def _texts(value, name):
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    for pid, text in value.items():
        if not ID_RE.match(pid) or not isinstance(text, str) or len(text) > MAX_TEXT:
            raise ValueError(f"bad {name} entry {pid!r}")
    return value


def validate(req):
    if not isinstance(req, dict):
        raise ValueError("body must be an object")
    out = {"code": _texts(req.get("code", {}), "code"), "pseudo": _texts(req.get("pseudo", {}), "pseudo"),
           "full": bool(req.get("full"))}
    solved = req.get("solvedAt", {})
    if not isinstance(solved, dict) or not all(ID_RE.match(k) and isinstance(v, (int, float)) for k, v in solved.items()):
        raise ValueError("bad solvedAt")
    out["solvedAt"] = {k: int(v) for k, v in solved.items()}
    lessons = req.get("lessonsDone", [])
    if not isinstance(lessons, list) or not all(isinstance(n, int) and 0 < n < 100 for n in lessons):
        raise ValueError("bad lessonsDone")
    out["lessonsDone"] = lessons
    attempts = req.get("attempts", [])
    if not isinstance(attempts, list) or len(attempts) > 500:
        raise ValueError("bad attempts")
    for a in attempts:
        if not (isinstance(a, dict) and ID_RE.match(str(a.get("id", ""))) and a.get("mode") in ("samples", "submit")
                and all(isinstance(a.get(k), int) for k in ("passed", "total", "t"))):
            raise ValueError("bad attempt")
        fail = a.get("fail")
        if fail is not None and not (isinstance(fail, dict) and isinstance(fail.get("timeout", False), bool) and all(
                isinstance(fail.get(k, ""), str) and len(fail.get(k, "")) <= n for k, n in FAIL_TEXT.items())):
            raise ValueError("bad attempt fail")
    out["attempts"] = attempts
    return out


def _read_texts(folder: Path, suffix: str):
    return {p.stem: p.read_text(encoding="utf-8") for p in folder.glob(f"*{suffix}")} if folder.exists() else {}


def sync(req, data: Path | None = None):
    """Merge one browser update into the folder. Returns what the browser should know."""
    data = data or DATA  # read at call time, so changing DATA (or a test) takes effect
    req = validate(req)
    with LOCK:
        data.mkdir(parents=True, exist_ok=True)
        if not (data / "agent.md").exists():
            _write(data / "agent.md", AGENT_MD)

        for kind, folder, suffix in (("code", "code", ".py"), ("pseudo", "pseudocode", ".md")):
            for pid, text in req[kind].items():
                path = data / folder / f"{pid}{suffix}"
                if not text.strip():
                    path.unlink(missing_ok=True)
                elif not path.exists() or path.read_text(encoding="utf-8") != text:
                    _write(path, text)

        progress_path = data / "progress.json"
        progress = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.exists() else {}
        solved = dict(progress.get("solvedAt", {}))  # a copy, so the "changed?" check below compares old vs new
        for pid, t in req["solvedAt"].items():
            solved[pid] = max(t, solved.get(pid, t))
        lessons = sorted(set(progress.get("lessonsDone", [])) | set(req["lessonsDone"]))
        new_progress = {"version": 1, "solvedAt": solved, "lessonsDone": lessons}
        if new_progress != {k: progress.get(k) for k in new_progress}:
            _write(progress_path, json.dumps({**new_progress, "updated": datetime.now().isoformat(timespec="seconds")}, indent=2))

        if req["attempts"]:
            path = data / "attempts.csv"
            new_file = not path.exists()
            with path.open("a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if new_file:
                    w.writerow(ATTEMPT_FIELDS)
                for a in req["attempts"]:
                    when = datetime.fromtimestamp(a["t"] / 1000).isoformat(timespec="seconds")
                    w.writerow([when, a["id"], a["mode"], a["passed"], a["total"]])
            failed = [a for a in req["attempts"] if a.get("fail") and a["passed"] < a["total"]]
            if failed:
                with (data / "mistakes.jsonl").open("a", encoding="utf-8", newline="\n") as f:
                    for a in failed:
                        row = {"t": a["t"], "time": datetime.fromtimestamp(a["t"] / 1000).isoformat(timespec="seconds"),
                               "problem": a["id"], "mode": a["mode"], **{k: a["fail"].get(k, "") for k in FAIL_TEXT},
                               "timeout": a["fail"].get("timeout", False)}
                        f.write(json.dumps(row) + "\n")

        code = _read_texts(data / "code", ".py")
        analytics = analyze(code, _read_attempts(data / "attempts.csv"), solved, _read_mistakes(data / "mistakes.jsonl"))
        _write_if_changed(data / "analytics.json", json.dumps(analytics, indent=2))
        _write_if_changed(data / "analytics.md", analytics_md(analytics))

        reply = {"folder": str(data), "solvedAt": solved, "lessonsDone": lessons, "analytics": analytics}
        if req["full"]:  # give a new or cleared browser back the work it doesn't have
            reply["code"] = {k: v for k, v in code.items() if k not in req["code"]}
            reply["pseudo"] = {k: v for k, v in _read_texts(data / "pseudocode", ".md").items() if k not in req["pseudo"]}
        return reply


def _write_if_changed(path: Path, text: str):
    # analytics carry no timestamp, so unchanged code doesn't rewrite the files
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        _write(path, text)


def _read_attempts(path: Path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("problem")]


def _read_mistakes(path: Path):
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass  # a half-written last line from a crash; the rest still counts
    return out


EXAMPLE_LINES = 60


def mistake_stats(records, solved):
    """Failed runs sorted into groups and kinds. Re-running the same code on the same problem counts once.
    shortcut: re-sorts every record on every sync; fine for thousands, cache per line if it gets slow."""
    last_code, kinds, per_problem = {}, {}, defaultdict(Counter)
    for r in sorted(records, key=lambda r: r.get("t", 0)):
        pid, src = r.get("problem", ""), r.get("code", "")
        if last_code.get(pid) == src:
            continue
        last_code[pid] = src
        m = mistakes.classify(src, r.get("input", ""), r.get("expected", ""), r.get("got", ""), r.get("error", ""), r.get("timeout", False))
        k = kinds.setdefault(m["kind"], {"kind": m["kind"], "title": m["title"], "tip": m["tip"], "group": m["group"],
                                         "learn": m["learn"], "learnLabel": m["learnLabel"],
                                         "count": 0, "problems": set(), "fixed": set()})
        k["count"] += 1
        k["problems"].add(pid)
        if solved.get(pid, -1) > r.get("t", 0):
            k["fixed"].add(pid)  # solved after making this mistake
        k["example"] = {"problem": pid, "time": r.get("time", ""), "detail": m["detail"], "line": m["line"],
                        "code": "\n".join(src.splitlines()[:EXAMPLE_LINES])}
        per_problem[pid][m["title"]] += 1
    groups = {}
    for k in kinds.values():
        g = groups.setdefault(k["group"], {"group": k["group"], "title": mistakes.GROUPS[k["group"]], "count": 0, "kinds": []})
        g["count"] += k["count"]
        g["kinds"].append({**k, "problems": sorted(k["problems"]), "fixed": len(k["fixed"])})
    for g in groups.values():
        g["kinds"].sort(key=lambda k: (-k["count"], k["title"]))
    return {
        "total": sum(g["count"] for g in groups.values()),
        "groups": sorted(groups.values(), key=lambda g: (-g["count"], g["title"])),
        "byProblem": {pid: [{"title": t, "count": n} for t, n in c.most_common()] for pid, c in per_problem.items()},
    }


CONSTRUCTS = [
    (ast.For, "for loop"), (ast.While, "while loop"), (ast.If, "if / elif"), (ast.Try, "try / except"),
    ((ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp), "comprehension"), (ast.FunctionDef, "def (own function)"),
    (ast.Lambda, "lambda"), (ast.JoinedStr, "f-string"), (ast.Slice, "slicing"), (ast.With, "with (opening files)"),
    (ast.Break, "break"), (ast.Continue, "continue"),
]


def code_features(src: str):
    """Function calls and constructs in one file. Raises SyntaxError if the code doesn't parse."""
    tree = ast.parse(src)
    modules = {a.asname or a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported = {a.asname or a.name: f"{n.module}.{a.name}" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    own = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    calls, constructs = Counter(), Counter()
    for node in ast.walk(tree):
        for kinds, name in CONSTRUCTS:
            if isinstance(node, kinds):
                constructs[name] += 1
        if isinstance(node, ast.FunctionDef) and any(
                isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == node.name for c in ast.walk(node)):
            constructs["recursion"] += 1
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if isinstance(f, ast.Name):
            if f.id not in own:  # calls to your own functions aren't Python tools
                calls[imported.get(f.id, f.id) + "()"] += 1
        elif isinstance(f, ast.Attribute):
            if isinstance(f.value, ast.Name) and f.value.id in modules:
                calls[f"{f.value.id}.{f.attr}()"] += 1
            elif isinstance(f.value, ast.Name) and f.value.id in imported:
                calls[f"{imported[f.value.id]}.{f.attr}()"] += 1
            else:
                calls[f".{f.attr}()"] += 1
    return calls, constructs


def analyze(code: dict, attempts: list, solved: dict, mistake_records=()):
    uses, where = Counter(), defaultdict(set)
    c_uses, c_where = Counter(), defaultdict(set)
    unparsable = []
    for pid, src in sorted(code.items()):
        try:
            calls, constructs = code_features(src)
        except SyntaxError:
            unparsable.append(pid)
            continue
        for name, n in calls.items():
            uses[name] += n
            where[name].add(pid)
        for name, n in constructs.items():
            c_uses[name] += n
            c_where[name].add(pid)
    per = defaultdict(lambda: {"runs": 0, "submits": 0, "passedSubmits": 0, "last": ""})
    for a in attempts:
        p = per[a["problem"]]
        p["runs" if a["mode"] == "samples" else "submits"] += 1
        if a["mode"] == "submit" and a["passed"] == a["total"]:
            p["passedSubmits"] += 1
        p["last"] = max(p["last"], a["time"])
    rank = lambda c, w: [{"name": k, "uses": v, "problems": sorted(w[k])} for k, v in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))]
    return {
        "problemsWithCode": len(code), "unparsable": unparsable, "solved": len(solved),
        "functions": rank(uses, where), "constructs": rank(c_uses, c_where),
        "mistakes": mistake_stats(mistake_records, solved),
        "attempts": sorted(({"id": k, **v, "solved": k in solved} for k, v in per.items()),
                           key=lambda r: (-(r["runs"] + r["submits"]), r["id"])),
    }


def analytics_md(a):
    out = io.StringIO()
    out.write("# Analytics\n\nRebuilt by the practice site on every save. Do not edit; see agent.md.\n\n")
    out.write(f"- Problems with code: {a['problemsWithCode']}\n- Problems solved: {a['solved']}\n")
    if a["unparsable"]:
        out.write(f"- Not counted (code has a syntax error): {', '.join(a['unparsable'])}\n")
    out.write("\n## Functions you use most\n\n| Function | Uses | Problems |\n|---|---|---|\n")
    for f in a["functions"]:
        out.write(f"| `{f['name']}` | {f['uses']} | {len(f['problems'])} |\n")
    out.write("\n## How you write it\n\n| Construct | Uses | Problems |\n|---|---|---|\n")
    for c in a["constructs"]:
        out.write(f"| {c['name']} | {c['uses']} | {len(c['problems'])} |\n")
    m = a["mistakes"]
    out.write(f"\n## Mistakes ({m['total']})\n\n| Group | Mistake | Times | Problems | Fixed later |\n|---|---|---|---|---|\n")
    for g in m["groups"]:
        for k in g["kinds"]:
            out.write(f"| {g['title']} | {k['title']} | {k['count']} | {', '.join(k['problems'])} | {k['fixed']} |\n")
    out.write("\n## Attempts per problem\n\n| Problem | Sample runs | Submits | Passed submits | Solved | Last try |\n|---|---|---|---|---|---|\n")
    for r in a["attempts"]:
        out.write(f"| {r['id']} | {r['runs']} | {r['submits']} | {r['passedSubmits']} | {'yes' if r['solved'] else 'no'} | {r['last']} |\n")
    return out.getvalue()


if __name__ == "__main__":  # self-check against a temp folder
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        src = "import math\nfrom datetime import date\ndef f(n):\n    return 1 if n < 2 else n * f(n - 1)\n" \
              "s = input().strip()\nprint(s.split()[0], math.sqrt(4), date.today(), f(3), [c for c in s])\n"
        r = sync({"code": {"pf-a": src, "pf-b": "print(1"}, "pseudo": {"pf-a": "read, split"},
                  "solvedAt": {"pf-a": 5}, "lessonsDone": [2],
                  "attempts": [{"id": "pf-a", "mode": "submit", "passed": 3, "total": 3, "t": 1}], "full": True}, d)
        names = {f["name"]: f["uses"] for f in r["analytics"]["functions"]}
        assert names == {"input()": 1, ".strip()": 1, "print()": 1, ".split()": 1, "math.sqrt()": 1,
                         "datetime.date.today()": 1}, names
        assert "f()" not in names, "own functions are not counted"
        cons = {c["name"] for c in r["analytics"]["constructs"]}
        assert {"recursion", "comprehension", "def (own function)"} <= cons, cons
        assert r["analytics"]["unparsable"] == ["pf-b"]
        assert (d / "code" / "pf-a.py").read_text(encoding="utf-8") == src and (d / "agent.md").exists()
        # A fresh browser gets its work back; an empty text deletes the file; solvedAt keeps the later time.
        r2 = sync({"solvedAt": {"pf-a": 3}, "full": True}, d)
        assert r2["code"]["pf-a"] == src and r2["pseudo"] == {"pf-a": "read, split"} and r2["solvedAt"]["pf-a"] == 5
        assert json.loads((d / "progress.json").read_text(encoding="utf-8"))["solvedAt"] == {"pf-a": 5}, "solve not saved"
        sync({"code": {"pf-b": ""}}, d)
        assert not (d / "code" / "pf-b.py").exists()
        for bad in ({"code": {"../x": "a"}}, {"code": {"a": 1}}, {"attempts": [{"id": "a"}]}, []):
            try:
                validate(bad)
                raise AssertionError(f"accepted {bad}")
            except ValueError:
                pass
        assert (d / "attempts.csv").read_text(encoding="utf-8").startswith("time,problem,mode,passed,total")
        bug = "s = input()\nz = 0\nfor x in s:\n    z += 1\nprint(x)\n"
        fail = {"code": bug, "input": "abc", "expected": "3", "got": "c", "error": ""}
        twice = [{"id": "pf-v", "mode": "submit", "passed": 0, "total": 2, "t": 10, "fail": fail},
                 {"id": "pf-v", "mode": "submit", "passed": 0, "total": 2, "t": 11, "fail": fail}]
        r3 = sync({"attempts": twice, "solvedAt": {"pf-v": 20}}, d)
        m = r3["analytics"]["mistakes"]
        assert m["total"] == 1, "the same code submitted twice is one mistake"
        k = m["groups"][0]["kinds"][0]
        assert (k["kind"], k["fixed"], k["example"]["line"]) == ("wrong-variable", 1, 5), k
        assert m["byProblem"]["pf-v"] == [{"title": "Printed the wrong variable", "count": 1}]
        assert "Printed the wrong variable" in (d / "analytics.md").read_text(encoding="utf-8")
        for bad in ({"attempts": [{**twice[0], "fail": {"code": 5}}]}, {"attempts": [{**twice[0], "fail": "x"}]}):
            try:
                validate(bad)
                raise AssertionError(f"accepted {bad}")
            except ValueError:
                pass
    print("notes_store self-check passed")
