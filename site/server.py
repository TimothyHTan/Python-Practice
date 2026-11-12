"""Local-only server: serves the site and forwards AI requests to the Claude Code CLI
(through your CLI tool proxy when ~/.claude/settings.json sets ANTHROPIC_BASE_URL).

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
import time
import urllib.request
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
# Models offered by your CLI tool (the proxy in ~/.claude/settings.json) are allowed too, see allowed_models().
MODELS = {"", "haiku", "sonnet", "opus", "fable"}
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")
IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
MAX_IMAGES = 4
MAX_IMAGE_B64 = 6_000_000
EFFORTS = {"", "low", "medium", "high", "xhigh", "max"}
CLAUDE = shutil.which("claude")

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
    base = {**os.environ, **claude_env()}.get("ANTHROPIC_BASE_URL", "")
    return f"Claude Code via your CLI tool ({base.split('//')[-1].rstrip('/')})" if base else "Claude Code (your Claude login)"


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


def allowed_models() -> set:
    return MODELS | set(proxy_models())


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


def load_settings():
    try:
        folder = json.loads(SETTINGS.read_text(encoding="utf-8")).get("folder")
    except (OSError, ValueError):
        return
    if folder:
        notes_store.DATA = Path(folder)


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
    if new == notes_store.DEFAULT:
        SETTINGS.unlink(missing_ok=True)
    else:
        SETTINGS.write_text(json.dumps({"folder": str(new)}, indent=2), encoding="utf-8")


def settings_info() -> dict:
    return {"folder": str(notes_store.DATA), "default": str(notes_store.DEFAULT),
            "claude": CLAUDE or "", "route": route(), "models": proxy_models()}


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
            return self._json(200, {"route": route(), "models": proxy_models()})
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
                set_folder(json.loads(self.rfile.read(length)).get("folder"))
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
            reply = ask_claude(PROMPTS[kind].format(problem=problem, text=text), model, effort, SYSTEMS.get(kind, SYSTEM), images)
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
