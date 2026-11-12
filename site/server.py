"""Local-only server: serves the site and forwards AI requests to the Claude Code CLI
(through your CLI tool proxy when ~/.claude/settings.json sets ANTHROPIC_BASE_URL) or to the Codex CLI,
whichever is picked on the Settings page.

Run from anywhere:  py site/server.py   then open http://localhost:8000/site/
"""
import base64
import binascii
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import notes_store  # saves progress to Documents/python notes (or the folder picked on the Settings page)

ROOT = Path(__file__).resolve().parent.parent  # the repo folder, so pages live under /site/
SETTINGS = Path(__file__).with_name("settings.local.json")  # this computer's choices; kept out of git
PORT = 8000
MAX_CHARS = 8000
MAX_BODY = 20_000_000  # a full sync, or a chat message with a few pictures
TIMEOUT_S = 300  # max effort on a big model can take a few minutes
# Only these values ever reach the command line; "" means "use the CLI's default".
# Models offered by your CLI tool (the proxy in ~/.claude/settings.json) or by Codex are allowed too, see model_options().
CLAUDE_MODELS = [("haiku", "Haiku 5.5 (fastest)"), ("sonnet", "Sonnet 5.5"), ("opus", "Opus 5.5"), ("fable", "Fable 5.2 (most capable)")]
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")
IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
MAX_IMAGES = 4
MAX_IMAGE_B64 = 6_000_000
EFFORTS = {"", "low", "medium", "high", "xhigh", "max"}
CLAUDE = shutil.which("claude")
CODEX = shutil.which("codex")
PROVIDERS = {"claude": "Claude Code", "codex": "Codex"}
provider = "claude"  # which CLI answers; picked on the Settings page
CODEX_SCAN = Path(__file__).with_name("codex_models.local.json")  # which Codex models this account can run
# Phrases Codex uses when an account may not use a model (e.g. "...is not supported when using Codex with a ChatGPT account").
UNAVAILABLE = ("not supported", "not available", "does not have access", "do not have access", "does not exist", "model_not_found")
SCAN_LOCK = threading.Lock()
scanning = threading.Event()
IMAGE_EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp"}

SYSTEM = (
    "You are a patient Python tutor inside a practice website. The student is a beginner. "
    "Never write the full Python solution. Give short, concrete feedback in plain text "
    "(no markdown headings), under 150 words. Use simple words."
)

# The chat helper (the gem on the practice page) may write code: the student asks it to add functions.
CHAT_SYSTEM = (
    "You are the helper inside a Python practice website. The student is a beginner preparing for a school exam. "
    "You can see the current problem, the student's code and the conversation so far. Answer the latest message. "
    "Be short and concrete, use simple words, no headings. When the student asks for a function or other code, "
    "give it in one ```python block that can be pasted into their file as is, then explain it in a few lines. "
    "Follow the problem's exact output format. If they ask for the complete solution to the current problem, "
    "give it, but walk through each step so they learn it. Otherwise prefer the smallest piece of code that helps."
)
SYSTEMS = {"chat": CHAT_SYSTEM}
LIMITS = {"chat": 20000}  # a conversation needs more room than one question

PROMPTS = {
    "chat": "PROBLEM:\n{problem}\n\nCONVERSATION (latest message last):\n{text}",
    "pseudo": "Here is a practice problem and the student's pseudocode plan.\n"
              "Say whether the plan would solve the problem, point out any missing step or edge case, "
              "and suggest which Python features to use for each step.\n\nPROBLEM:\n{problem}\n\nPSEUDOCODE:\n{text}",
    "hint": "Give one small hint (not the answer) for this problem, based on the student's current code.\n\n"
            "PROBLEM:\n{problem}\n\nCODE:\n{text}",
    "explain": "The student's code failed. Explain in plain words why it failed and what to look at, "
               "without giving the fixed code.\n\nPROBLEM:\n{problem}\n\nCODE AND RESULT:\n{text}",
}


def claude_env() -> dict:
    """Your Claude Code settings' env block (e.g. ANTHROPIC_BASE_URL pointing at your CLI tool proxy).
    We skip user settings below (to keep your hooks/plugins out), so pass these through ourselves."""
    try:
        env = json.loads((Path.home() / ".claude" / "settings.json").read_text(encoding="utf-8")).get("env", {})
    except (OSError, ValueError):
        env = {}
    return {k: str(v) for k, v in env.items() if k.startswith("ANTHROPIC_")}


def route() -> str:
    if provider == "codex":
        return "Codex CLI (your ChatGPT / OpenAI login)"
    base = {**os.environ, **claude_env()}.get("ANTHROPIC_BASE_URL", "")
    return f"Claude Code via your CLI tool ({base.split('//')[-1].rstrip('/')})" if base else "Claude Code (your Claude login)"


def route_name() -> str:
    """Short label for the helper panel."""
    if provider == "codex":
        return "Codex"
    return "Claude Code + CLI tool" if {**os.environ, **claude_env()}.get("ANTHROPIC_BASE_URL") else "Claude Code"


_models_cache = (0.0, [])


def proxy_models() -> list:
    """Model ids your CLI tool offers (cached for 5 minutes). Empty when there's no proxy or it's not running."""
    global _models_cache
    if time.time() - _models_cache[0] < 300:
        return _models_cache[1]
    env = {**os.environ, **claude_env()}
    base, token = env.get("ANTHROPIC_BASE_URL", ""), env.get("ANTHROPIC_AUTH_TOKEN") or env.get("ANTHROPIC_API_KEY", "")
    ids = []
    if base:
        try:
            req = urllib.request.Request(base.rstrip("/") + "/v1/models", headers={
                "Authorization": f"Bearer {token}", "x-api-key": token, "anthropic-version": "2023-06-01"})
            with urllib.request.urlopen(req, timeout=4) as res:
                data = json.load(res)
            ids = sorted({m["id"] for m in data.get("data", []) if MODEL_RE.match(str(m.get("id", "")))}, reverse=True)
        except (OSError, ValueError, KeyError):
            ids = []
    _models_cache = (time.time(), ids)
    return ids


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def codex_cache() -> dict:
    """Codex's own model list (written by the codex CLI once it has run signed in), best model first."""
    return read_json(Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "models_cache.json")


def codex_models() -> list:
    """Every model Codex lists. A free account may not be allowed to run all of them: see usable_codex_models()."""
    models = codex_cache().get("models")
    if not isinstance(models, list):
        return []
    return [(m["slug"], str(m.get("display_name") or m["slug"])) for m in models
            if isinstance(m, dict) and m.get("visibility") == "list" and MODEL_RE.match(str(m.get("slug", "")))]


def current_scan() -> dict:
    """The last scan, if it was for the account and model list Codex has now."""
    scan, cache = read_json(CODEX_SCAN), codex_cache()
    fresh = cache and scan.get("identity") == cache.get("identity") and scan.get("checked") == [m for m, _ in codex_models()]
    return scan if fresh else {}


def usable_codex_models() -> list:
    """The listed models this account can run (all of them until the first scan finishes)."""
    scan = current_scan()
    return [(m, label) for m, label in codex_models() if not scan or m in scan["usable"]]


def scan_codex(force: bool = False):
    """In the background, send each listed model a tiny prompt and keep the ones that answer.
    Free ChatGPT accounts get only some models (e.g. Luna); paid plans get more. Rescans when the account
    or Codex's model list changes, or when asked from the Settings page."""
    with SCAN_LOCK:
        if not CODEX or scanning.is_set() or (current_scan() and not force):
            return
        scanning.set()

    def probe(model):
        try:
            ask_codex("Reply with the word OK.", model, "low", "", timeout=120)
        except RuntimeError as e:
            return not any(p in str(e).lower() for p in UNAVAILABLE)  # other errors (offline, limits): keep it listed
        except subprocess.TimeoutExpired:
            return True
        return True

    def work():
        try:
            if not codex_cache():
                probe("")  # Codex writes its model cache on its first run
            listed = [m for m, _ in codex_models()]
            with ThreadPoolExecutor(4) as pool:
                ok = list(pool.map(probe, listed))
            usable = [m for m, good in zip(listed, ok) if good]
            CODEX_SCAN.write_text(json.dumps({"identity": codex_cache().get("identity"), "checked": listed,
                                              "usable": usable or listed, "scanned_at": time.time()}, indent=2), encoding="utf-8")
        finally:
            scanning.clear()

    threading.Thread(target=work, daemon=True).start()


def model_options() -> list:
    """(id, label) pairs for the model picker of the active provider; "" (the CLI's default) is always allowed too."""
    if provider == "codex":
        scan_codex()  # no-op while a scan runs or the last one still matches
        return usable_codex_models()
    return CLAUDE_MODELS + [(m, f"{m} (CLI tool)") for m in proxy_models()]


def allowed_models() -> set:
    return {""} | {m for m, _ in model_options()}


def ask(prompt: str, model: str = "", effort: str = "", system: str = SYSTEM, images=()) -> str:
    return (ask_codex if provider == "codex" else ask_claude)(prompt, model, effort, system, images)


def ask_codex(prompt: str, model: str = "", effort: str = "", system: str = SYSTEM, images=(), timeout=TIMEOUT_S) -> str:
    if not CODEX:
        raise RuntimeError("Codex CLI not found on PATH. Install it or check `codex --version`.")
    if not model and current_scan():
        model = current_scan()["usable"][0]  # "Default" = the best model this account can run, not one it can't
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        answer = work / "answer.txt"
        # Your Codex config (hooks, MCP servers, notify) stays out; auth still comes from ~/.codex.
        # Read-only sandbox in an empty temp folder, so the agent can't change anything.
        cmd = [CODEX, "exec", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config", "--ignore-rules",
               "--sandbox", "read-only", "--cd", str(work), "--color", "never", "--output-last-message", str(answer)]
        if model:
            cmd += ["--model", model]
        if effort:
            cmd += ["--config", f"model_reasoning_effort={effort}"]  # no quotes: Windows runs codex.cmd through cmd.exe
        for n, image in enumerate(images):
            path = work / f"picture{n}{IMAGE_EXT[image['media_type']]}"
            path.write_bytes(base64.b64decode(image["data"]))
            cmd += ["--image", str(path)]
        # No positional prompt: codex reads it from stdin. Codex has no system-prompt flag, so it leads the prompt.
        out = subprocess.run(cmd, input=f"{system}\n\n{prompt}", capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=timeout, cwd=work)
        reply = answer.read_text(encoding="utf-8").strip() if answer.exists() else ""
    if out.returncode or not reply:
        raise RuntimeError(out.stderr.strip()[-500:] or "Codex exited without an answer.")
    return reply


def ask_claude(prompt: str, model: str = "", effort: str = "", system: str = SYSTEM, images=()) -> str:
    if not CLAUDE:
        raise RuntimeError("Claude Code CLI not found on PATH. Install it or check `claude --version`.")
    # Skip user settings/plugins/MCP so your own Claude Code hooks don't change the tutor's behaviour.
    # stream-json input lets the message carry pictures next to the text.
    cmd = [CLAUDE, "-p", "--tools", "", "--system-prompt", system,
           "--no-session-persistence", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
           "--setting-sources", "project", "--strict-mcp-config", "--disable-slash-commands"]
    if model:
        cmd += ["--model", model]
    if effort:
        cmd += ["--effort", effort]
    content = [{"type": "image", "source": {"type": "base64", "media_type": i["media_type"], "data": i["data"]}} for i in images]
    content.append({"type": "text", "text": prompt})
    message = json.dumps({"type": "user", "message": {"role": "user", "content": content}})
    out = subprocess.run(cmd, input=message + "\n", capture_output=True, text=True, encoding="utf-8",
                         timeout=TIMEOUT_S, env={**os.environ, **claude_env()})
    for line in reversed(out.stdout.splitlines()):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "result":
            if event.get("is_error"):
                raise RuntimeError(str(event.get("result") or "Claude Code reported an error."))
            return str(event.get("result", "")).strip()
    raise RuntimeError(out.stderr.strip()[-500:] or "Claude CLI exited without an answer.")


def read_settings() -> dict:
    try:
        data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_setting(key: str, value):
    """Store one choice; None drops it (back to the default)."""
    data = read_settings()
    if value is None:
        data.pop(key, None)
    else:
        data[key] = value
    if data:
        SETTINGS.write_text(json.dumps(data, indent=2), encoding="utf-8")
    else:
        SETTINGS.unlink(missing_ok=True)


def load_settings():
    global provider
    data = read_settings()
    if data.get("folder"):
        notes_store.DATA = Path(data["folder"])
    if data.get("ai") in PROVIDERS:
        provider = data["ai"]


def set_provider(raw) -> None:
    global provider
    if raw not in PROVIDERS:
        raise ValueError("unknown AI tool")
    provider = raw
    save_setting("ai", None if raw == "claude" else raw)


def set_folder(raw) -> None:
    """Switch the save folder. Copies your saved work over when the new folder is empty, so history comes along."""
    if not isinstance(raw, str) or len(raw) > 1000:
        raise ValueError("folder must be text")
    new = Path(raw.strip()).expanduser() if raw.strip() else notes_store.DEFAULT
    if not new.is_absolute():
        raise ValueError("use a full path, like C:\\Users\\you\\Documents\\python notes or ~/Documents/python notes")
    if new.exists() and not new.is_dir():
        raise ValueError("that path is a file, not a folder")
    old = notes_store.DATA
    if old.resolve() in new.resolve().parents:
        raise ValueError("pick a folder outside the current save folder")
    with notes_store.LOCK:
        if new != old and old.is_dir() and not (new.exists() and any(new.iterdir())):
            shutil.copytree(old, new, dirs_exist_ok=True)
        new.mkdir(parents=True, exist_ok=True)
        notes_store.DATA = new
    save_setting("folder", None if new == notes_store.DEFAULT else str(new))


def settings_info() -> dict:
    return {"folder": str(notes_store.DATA), "default": str(notes_store.DEFAULT), **ai_info(),
            "clis": {"claude": CLAUDE or "", "codex": CODEX or ""}}


def ai_info() -> dict:
    models = model_options()  # may start a Codex model scan, so read `scanning` after it
    return {"provider": provider, "providers": PROVIDERS, "route": route(), "name": route_name(),
            "models": models, "scanning": scanning.is_set()}


def open_folder(path: Path):
    if os.name == "nt":
        os.startfile(path)  # File Explorer
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def check_images(images) -> list:
    if not isinstance(images, list) or len(images) > MAX_IMAGES:
        raise ValueError(f"send at most {MAX_IMAGES} pictures")
    for i in images:
        if not isinstance(i, dict) or i.get("media_type") not in IMAGE_TYPES \
                or not isinstance(i.get("data"), str) or len(i["data"]) > MAX_IMAGE_B64:
            raise ValueError("pictures must be PNG, JPEG, GIF or WebP and under about 4 MB")
        try:
            base64.b64decode(i["data"], validate=True)
        except binascii.Error:
            raise ValueError("a picture is not valid base64") from None
    return [{"media_type": i["media_type"], "data": i["data"]} for i in images]


class Handler(SimpleHTTPRequestHandler):
    # Windows registry can map .js to text/plain, which breaks ES modules.
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      ".js": "text/javascript", ".mjs": "text/javascript",
                      ".json": "application/json", ".glb": "model/gltf-binary"}

    def end_headers(self):
        # Always check for a newer file, so edits show up on a normal reload (not stale CSS/JS).
        self.send_header("Cache-Control", "no-cache")
        # Cross-origin isolation, so the page can stop an endless loop with a KeyboardInterrupt (SharedArrayBuffer)
        # instead of restarting Python. "credentialless" still lets the CDN scripts and Google Fonts load.
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "credentialless")
        super().end_headers()

    def do_GET(self):
        if self.path == "/api/ai-info":  # which route the helper uses and the models it can pick
            return self._json(200, ai_info())
        if self.path == "/api/settings":
            return self._json(200, settings_info())
        return super().do_GET()

    def do_POST(self):
        # Only this site may call the API: other websites could otherwise post here from your browser.
        origin = self.headers.get("Origin")
        if origin not in (None, f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}") \
                or not self.headers.get("Content-Type", "").startswith("application/json"):
            return self._json(403, {"error": "Requests must come from the practice site."})
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_BODY:
            return self._json(413, {"error": "Request too large."})
        if self.path == "/api/sync":
            try:
                return self._json(200, notes_store.sync(json.loads(self.rfile.read(length))))
            except (ValueError, TypeError) as e:
                return self._json(400, {"error": f"Bad request: {e}"})
        if self.path == "/api/open-folder":
            notes_store.DATA.mkdir(parents=True, exist_ok=True)
            try:
                open_folder(notes_store.DATA)
            except OSError as e:
                return self._json(500, {"error": f"Could not open the folder ({e}). It is {notes_store.DATA}"})
            return self._json(200, {"folder": str(notes_store.DATA)})
        if self.path == "/api/settings":
            try:
                body = json.loads(self.rfile.read(length))
                if "ai" in body:
                    set_provider(body["ai"])
                if "folder" in body:
                    set_folder(body["folder"])
                if body.get("scan"):
                    scan_codex(force=True)
            except (ValueError, TypeError, AttributeError) as e:
                return self._json(400, {"error": str(e)})
            except OSError as e:
                return self._json(500, {"error": f"Could not use that folder: {e}"})
            return self._json(200, settings_info())
        if self.path != "/api/ai":
            return self.send_error(404)
        try:
            body = json.loads(self.rfile.read(length))
            kind, problem, text = body["kind"], str(body["problem"]), str(body["text"])
            model, effort = str(body.get("model", "")), str(body.get("effort", ""))
            images = check_images(body.get("images", [])) if kind == "chat" else []
            if model not in allowed_models() or effort not in EFFORTS:
                raise ValueError("unknown model or effort")
            if kind not in PROMPTS:
                raise ValueError("unknown kind")
            if not text.strip() or len(text) + len(problem) > LIMITS.get(kind, MAX_CHARS):
                raise ValueError("text is empty or too long")
        except (ValueError, KeyError, TypeError) as e:
            return self._json(400, {"error": f"Bad request: {e}"})
        try:
            reply = ask(PROMPTS[kind].format(problem=problem, text=text), model, effort, SYSTEMS.get(kind, SYSTEM), images)
            self._json(200, {"reply": reply})
        except subprocess.TimeoutExpired:
            self._json(504, {"error": f"The AI took longer than {TIMEOUT_S // 60} minutes. Try a lower effort or a faster model."})
        except RuntimeError as e:
            self._json(502, {"error": str(e)})

    def _json(self, code, data):
        raw = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


if __name__ == "__main__":
    load_settings()
    # 127.0.0.1 only: the AI endpoint runs a local CLI, so never expose it to the network.
    server = ThreadingHTTPServer(("127.0.0.1", PORT), partial(Handler, directory=str(ROOT)))
    print(f"Open http://localhost:{PORT}/site/   (Ctrl+C to stop)")
    server.serve_forever()
