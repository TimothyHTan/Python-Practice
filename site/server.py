"""Local-only server: serves the site and answers AI requests with Claude or Codex (picked on the Settings page).
When ~/.claude/settings.json points ANTHROPIC_BASE_URL at an API proxy (e.g. CLIProxyAPI) that has a login for the
tool, it calls the proxy directly over HTTP; otherwise it runs the `claude` or `codex` CLI.

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
import urllib.error
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
UNAVAILABLE = ("not supported", "not available", "does not have access", "do not have access", "does not exist",
               "model_not_found", "unknown provider", "no auth available")
SCAN_LOCK = threading.Lock()
scanning = threading.Event()
IMAGE_EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp"}
# The AI CLIs run in this empty folder, always the same one. Run from the project folder, Claude Code adds its
# memory notes for that folder (~400 extra tokens a call); a new folder each time changes the prompt, so the
# prompt cache never gets reused. Measured: a repeat hint here reads its whole prompt from cache.
AI_DIR = Path(tempfile.gettempdir()) / "vertical-world-ai"
# Codex is a full coding agent (~15k tokens of instructions and tool definitions a call). The tutor needs none of
# its tools, so these drop to ~5.5k. Written as -c settings: unknown ones are ignored, unlike --disable,
# so another Codex version can't break the helper.
CODEX_LEAN = [f"features.{f}=false" for f in (
    "shell_tool", "unified_exec", "apps", "browser_use", "computer_use", "image_generation", "multi_agent", "plugins",
    "goals", "skill_search", "tool_suggest", "sleep_tool", "view_image", "hooks", "in_app_browser")] + ["web_search=disabled"]
CODEX_BASE = "You answer questions for a Python practice website. You have no tools. Reply in plain text."

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


def proxy() -> tuple:
    """(base URL, key) of your API proxy (e.g. CLIProxyAPI), from ANTHROPIC_BASE_URL in ~/.claude/settings.json."""
    env = {**os.environ, **claude_env()}
    return env.get("ANTHROPIC_BASE_URL", "").rstrip("/"), env.get("ANTHROPIC_AUTH_TOKEN") or env.get("ANTHROPIC_API_KEY", "")


_models_cache = (0.0, [])


def proxy_models() -> list:
    """Model ids your API proxy offers (cached for 5 minutes). Empty when there's no proxy or it's not running."""
    global _models_cache
    if time.time() - _models_cache[0] < 300:
        return _models_cache[1]
    base, key = proxy()
    ids = []
    if base:
        try:  # OpenAI-style request: lists every logged-in provider's models, not only Claude's
            req = urllib.request.Request(base + "/v1/models", headers={"Authorization": f"Bearer {key}", "x-api-key": key})
            with urllib.request.urlopen(req, timeout=4) as res:
                data = json.load(res)
            ids = sorted({m["id"] for m in data.get("data", []) if MODEL_RE.match(str(m.get("id", "")))}, reverse=True)
        except (OSError, ValueError, KeyError, AttributeError):
            ids = []
    _models_cache = (time.time(), ids)
    return ids


def proxy_family(name: str) -> list:
    """The proxy's models for one tool: Claude models for Claude Code, GPT chat models for Codex."""
    if name == "claude":
        return [m for m in proxy_models() if m.startswith("claude-")]
    models = codex_cache().get("models")
    hidden = {m.get("slug") for m in models if isinstance(m, dict) and m.get("visibility") != "list"} if isinstance(models, list) else set()
    # Image generators can't answer questions; models Codex itself hides (like its reviewer) aren't for chatting.
    return [m for m in proxy_models() if m.startswith("gpt-") and not m.startswith("gpt-image") and m not in hidden]


def via_proxy(name: str = "") -> bool:
    """Ask the proxy directly over HTTP (no CLI) when it has a login for that tool."""
    return bool(proxy_family(name or provider))


def route() -> str:
    host = proxy()[0].split("//")[-1]
    if via_proxy():
        return f"{PROVIDERS[provider]} models through your API proxy ({host}), no CLI"
    if provider == "codex":
        return "Codex CLI (your ChatGPT / OpenAI login)"
    return "Claude Code CLI (your Claude login)"


def route_name() -> str:
    """Short label for the helper panel."""
    return PROVIDERS[provider] + (" · API proxy" if via_proxy() else "")


def route_hint() -> str:
    """Why a tool isn't going through the proxy, when there is one."""
    if proxy()[0] and not via_proxy():
        if not proxy_models():
            return "Your API proxy isn't answering, so the CLI is used. Start the proxy, then reload."
        if provider == "codex":
            return ("Your API proxy has no Codex login, so the codex CLI is used. To send Codex through the proxy, "
                    "run the proxy once with -codex-login (CLIProxyAPI: cli-proxy-api -codex-login), then reload.")
    return ""


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
    """Every Codex model on the current route, best first. A free account may not be allowed to run all of them:
    see usable_codex_models()."""
    models = codex_cache().get("models")
    cached = [m for m in models if isinstance(m, dict)] if isinstance(models, list) else []
    names = {m.get("slug"): str(m.get("display_name") or m.get("slug")) for m in cached}
    if via_proxy("codex"):
        rank = {m.get("slug"): i for i, m in enumerate(cached)}  # Codex's own order where it knows the model
        ids = sorted(proxy_family("codex"), key=lambda m: (rank.get(m, len(rank)), m))
        return [(m, names.get(m, m)) for m in ids]
    return [(m["slug"], names[m["slug"]]) for m in cached
            if m.get("visibility") == "list" and MODEL_RE.match(str(m.get("slug", "")))]


def scan_identity() -> str:
    """Whose models a scan describes: the proxy, or the account the codex CLI is signed in to."""
    return f"proxy {proxy()[0]}" if via_proxy("codex") else str(codex_cache().get("identity") or "")


def current_scan() -> dict:
    """The last scan, if it was for the account and model list there is now."""
    scan = read_json(CODEX_SCAN)
    listed = [m for m, _ in codex_models()]
    fresh = listed and scan_identity() and scan.get("identity") == scan_identity() and scan.get("checked") == listed
    return scan if fresh else {}


def usable_codex_models() -> list:
    """The listed models this account can run (all of them until the first scan finishes)."""
    scan = current_scan()
    return [(m, label) for m, label in codex_models() if not scan or m in scan["usable"]]


def scan_codex(force: bool = False):
    """In the background, send each listed model a tiny prompt and keep the ones that answer.
    Free ChatGPT accounts get only some models (e.g. Luna); paid plans get more. Rescans when the account,
    the route or the model list changes, or when asked from the Settings page."""
    with SCAN_LOCK:
        if not (CODEX or via_proxy("codex")) or scanning.is_set() or (current_scan() and not force):
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
            if not codex_models() and CODEX:
                probe("")  # the codex CLI writes its model cache on its first run
            listed = [m for m, _ in codex_models()]
            with ThreadPoolExecutor(4) as pool:
                ok = list(pool.map(probe, listed))
            usable = [m for m, good in zip(listed, ok) if good]
            CODEX_SCAN.write_text(json.dumps({"identity": scan_identity(), "checked": listed,
                                              "usable": usable or listed, "scanned_at": time.time()}, indent=2), encoding="utf-8")
        finally:
            scanning.clear()

    threading.Thread(target=work, daemon=True).start()


def model_options() -> list:
    """(id, label) pairs for the model picker of the active provider; "" (the default) is always allowed too."""
    if provider == "codex":
        scan_codex()  # no-op while a scan runs or the last one still matches
        return usable_codex_models()
    return CLAUDE_MODELS + [(m, f"{m} (API proxy)") for m in proxy_family("claude")]


def allowed_models() -> set:
    return {""} | {m for m, _ in model_options()}


def ask(prompt: str, model: str = "", effort: str = "", system: str = SYSTEM, images=()) -> str:
    return (ask_codex if provider == "codex" else ask_claude)(prompt, model, effort, system, images)


def ask_codex(prompt: str, model: str = "", effort: str = "", system: str = SYSTEM, images=(), timeout=TIMEOUT_S) -> str:
    if not model:
        scan = current_scan()
        model = scan["usable"][0] if scan else ""  # "Default" = the best model this account can run, not one it can't
    if via_proxy("codex"):
        return ask_openai_api(prompt, model or codex_models()[0][0], effort, system, images, timeout)
    return ask_codex_cli(prompt, model, effort, system, images, timeout)


def ask_claude(prompt: str, model: str = "", effort: str = "", system: str = SYSTEM, images=()) -> str:
    if via_proxy("claude"):
        return ask_anthropic_api(prompt, model, effort, system, images)
    return ask_claude_cli(prompt, model, effort, system, images)


def proxy_post(path: str, body: dict, headers: dict, timeout=TIMEOUT_S) -> dict:
    base, _ = proxy()
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            err = json.loads(raw).get("error", raw)
            raw = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        except (ValueError, AttributeError):
            pass
        raise RuntimeError(f"API proxy error {e.code}: {raw[:500]}") from None
    except (OSError, ValueError) as e:  # proxy stopped, or timed out
        raise RuntimeError(f"Could not reach your API proxy ({e}).") from None


def claude_model_id(model: str) -> str:
    """haiku/sonnet/opus/fable -> the newest matching model the proxy has (e.g. claude-sonnet-5-5)."""
    ids = proxy_family("claude")
    if model in ids:
        return model
    alias = model or "sonnet"
    versions = [(tuple(int(n) for n in m.split("-")[2:]), m) for m in ids
                if re.fullmatch(rf"claude-{alias}-\d+(-\d)?", m)]  # skips dated ids like claude-sonnet-4-20250514
    if not versions:
        raise RuntimeError(f"Your API proxy has no {alias} model. Pick another one.")
    return max(versions)[1]


def ask_anthropic_api(prompt, model, effort, system, images) -> str:
    """One Messages API call through the proxy: just the tutor's prompt, no agent around it."""
    _, key = proxy()
    content = [{"type": "image", "source": {"type": "base64", "media_type": i["media_type"], "data": i["data"]}} for i in images]
    content.append({"type": "text", "text": prompt})
    body = {"model": claude_model_id(model), "max_tokens": 16000, "system": system,
            "messages": [{"role": "user", "content": content}]}
    if effort:
        body["output_config"] = {"effort": effort}
    data = proxy_post("/v1/messages", body, {"x-api-key": key, "Authorization": f"Bearer {key}", "anthropic-version": "2023-06-01"})
    reply = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
    if not reply:
        raise RuntimeError("The API proxy answered without any text.")
    return reply


def ask_openai_api(prompt, model, effort, system, images, timeout=TIMEOUT_S) -> str:
    """One Chat Completions call through the proxy for Codex (GPT) models."""
    _, key = proxy()
    content = [{"type": "text", "text": prompt}] + [
        {"type": "image_url", "image_url": {"url": f"data:{i['media_type']};base64,{i['data']}"}} for i in images]
    body = {"model": model, "messages": [{"role": "system", "content": system or "Reply briefly."},
                                         {"role": "user", "content": content}]}
    if effort:
        body["reasoning_effort"] = effort
    data = proxy_post("/v1/chat/completions", body, {"Authorization": f"Bearer {key}"}, timeout)
    try:
        reply = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        reply = ""
    if isinstance(reply, list):
        reply = "".join(part.get("text", "") for part in reply if isinstance(part, dict))
    if not str(reply or "").strip():
        raise RuntimeError("The API proxy answered without any text.")
    return str(reply).strip()


def ask_codex_cli(prompt, model, effort, system, images, timeout=TIMEOUT_S) -> str:
    if not CODEX:
        raise RuntimeError("Codex CLI not found on PATH. Install it or check `codex --version`.")
    AI_DIR.mkdir(exist_ok=True)
    base = AI_DIR / "codex-instructions.md"  # replaces Codex's long coding-agent instructions
    if not base.exists() or base.read_text(encoding="utf-8") != CODEX_BASE:
        base.write_text(CODEX_BASE, encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:  # this call's answer file and pictures
        work = Path(tmp)
        answer = work / "answer.txt"
        # Your Codex config (hooks, MCP servers, notify) stays out; auth still comes from ~/.codex.
        # Read-only sandbox in an empty folder, so the agent can't change anything.
        cmd = [CODEX, "exec", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config", "--ignore-rules",
               "--sandbox", "read-only", "--cd", str(AI_DIR), "--color", "never", "--output-last-message", str(answer),
               "--config", f"model_instructions_file={base.as_posix()}"]
        for setting in CODEX_LEAN:
            cmd += ["--config", setting]
        if model:
            cmd += ["--model", model]
        if effort:
            cmd += ["--config", f"model_reasoning_effort={effort}"]  # no quotes: Windows runs codex.cmd through cmd.exe
        for n, image in enumerate(images):
            path = work / f"picture{n}{IMAGE_EXT[image['media_type']]}"
            path.write_bytes(base64.b64decode(image["data"]))
            cmd += ["--image", str(path)]
        # No positional prompt: codex reads it from stdin. The tutor's own instructions lead the prompt, so they
        # still apply if a Codex version ignores model_instructions_file.
        out = subprocess.run(cmd, input=f"{system}\n\n{prompt}", capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=timeout, cwd=AI_DIR)
        reply = answer.read_text(encoding="utf-8").strip() if answer.exists() else ""
    if out.returncode or not reply:
        raise RuntimeError(out.stderr.strip()[-500:] or "Codex exited without an answer.")
    return reply


def ask_claude_cli(prompt, model, effort, system, images) -> str:
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
    AI_DIR.mkdir(exist_ok=True)
    out = subprocess.run(cmd, input=message + "\n", capture_output=True, text=True, encoding="utf-8",
                         timeout=TIMEOUT_S, env={**os.environ, **claude_env()}, cwd=AI_DIR)
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
            "clis": {"claude": CLAUDE or "", "codex": CODEX or ""},
            "ready": {name: bool(path) or via_proxy(name) for name, path in (("claude", CLAUDE), ("codex", CODEX))}}


def ai_info() -> dict:
    models = model_options()  # may start a Codex model scan, so read `scanning` after it
    return {"provider": provider, "providers": PROVIDERS, "route": route(), "name": route_name(),
            "models": models, "scanning": scanning.is_set(), "proxy": via_proxy(), "hint": route_hint()}


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
