# Vertical World: Python practice site

A local website for practising Python before an exam. It has practice problems that grade your code in the
browser, step-by-step lessons, a 7-day plan, a progress page that tracks your mistakes, notes, and an AI
helper that gives hints through the Claude Code or Codex CLI.

Everything runs on your own computer. A small Python server (`site/server.py`) serves the pages, saves your work
to a folder in Documents, and passes AI questions to the `claude` or `codex` command.

## What you need

- **Python 3.10 or newer** (only the standard library, so there is nothing to `pip install`)
- **Git**, to download the project
- A modern browser (Chrome, Edge or Firefox)
- An internet connection: your code runs in the browser with Pyodide, which loads from a CDN along with the fonts and the code editor
- **Optional:** an AI command-line tool for the AI helper (hints, plan checks, chat). Either one works:
  [Claude Code](https://docs.claude.com/en/docs/claude-code) (needs a Claude account) or
  [Codex](https://github.com/openai/codex) (needs a ChatGPT account). Everything else works without them.

---

## Windows 11

1. **Install Python and Git** (in PowerShell or Terminal):

   ```powershell
   winget install Python.Python.3.13
   winget install Git.Git
   ```

   Close and reopen the terminal afterwards so the `py` and `git` commands are found.

2. **Download the project:**

   ```powershell
   git clone https://github.com/TimothyHTan/Python-Practice.git
   cd Python-Practice
   ```

3. **Start it:** double-click `site\start.bat`, or run:

   ```powershell
   site\start.bat
   ```

   Your browser opens http://localhost:8000/site/. Keep the black window open while you use the site.
   Press `Ctrl+C` in it (or close it) to stop.

4. **Optional, for the AI helper:** install one of these (or both) and log in once.

   Claude Code:

   ```powershell
   irm https://claude.ai/install.ps1 | iex
   claude
   ```

   Codex (needs Node.js):

   ```powershell
   winget install OpenJS.NodeJS.LTS
   npm install -g @openai/codex
   codex
   ```

   Restart `start.bat` after installing so the server can find it. If you use Codex, pick it under
   **Settings → AI tool**. Claude Code is the default.

## Arch Linux

1. **Install Python and Git.** Use plain pacman:

   ```sh
   sudo pacman -S --needed python git xdg-utils
   ```

   or, if you use yay:

   ```sh
   yay -S --needed python git xdg-utils
   ```

   (`xdg-utils` lets the site's "Open folder" button open your file manager.)

2. **Download the project:**

   ```sh
   git clone https://github.com/TimothyHTan/Python-Practice.git
   cd Python-Practice
   ```

3. **Start it:**

   ```sh
   chmod +x site/start.sh   # only needed once, if it says "permission denied"
   ./site/start.sh
   ```

   It opens http://localhost:8000/site/ in your browser. If it doesn't, open that address yourself.
   Press `Ctrl+C` in the terminal to stop. Running `python site/server.py` from the project folder works too.

4. **Optional, for the AI helper:** install one of these (or both).

   Claude Code, from the AUR with yay:

   ```sh
   yay -S claude-code
   ```

   or without yay, with the official installer:

   ```sh
   curl -fsSL https://claude.ai/install.sh | bash
   ```

   Codex, with npm (install Node.js first with `sudo pacman -S --needed nodejs npm` or `yay -S --needed nodejs npm`):

   ```sh
   sudo npm install -g @openai/codex
   ```

   Run `claude` or `codex` once to log in, then restart the site. If you use Codex, pick it under
   **Settings → AI tool**. Claude Code is the default.

---

## Settings

Click **Settings** in the top bar:

- **Save folder:** where your work is saved. The default is `Documents/python notes` in your home folder
  (`C:\Users\<you>\Documents\python notes` on Windows, `~/Documents/python notes` on Linux).
  It sits apart from the project, so a `git pull` never touches your work, and clearing the browser doesn't lose it either.
  Switching to an empty folder copies your saved work over. The choice is stored in `site/settings.local.json`,
  which git ignores.
- **AI helper:** picks the AI tool (Claude Code or Codex), shows whether it is installed, and sets the default
  model and effort. The model list follows the tool you pick.

## The AI helper and your account

The AI features use your own login. No API key is stored in this project. There are two ways they connect:

**1. Through an API proxy (cheapest, used automatically when one is running).** If `~/.claude/settings.json` sets
`ANTHROPIC_BASE_URL` (and a token) pointing at a proxy such as [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI),
the server sends each question straight to the proxy over HTTP: Claude models through `/v1/messages`, Codex (GPT)
models through `/v1/chat/completions`. No CLI starts, and each hint is only the tutor's short instructions plus your
code (a few hundred tokens). A tool goes through the proxy when the proxy has a login for it. For CLIProxyAPI that means
`cli-proxy-api -claude-login` for Claude and `cli-proxy-api -codex-login` for Codex. The Settings page shows which
route each tool uses.

**2. Through the CLI (when there is no proxy).**

- **Claude Code:** runs `claude -p` with no tools and a short system prompt, so each call is one turn with about 500
  tokens of instructions. Your own hooks, plugins, MCP servers and memory files are skipped.
- **Codex:** runs `codex exec` read-only with Codex's tools switched off and short instructions (about 5,500 tokens
  instead of 15,000), without your `~/.codex/config.toml`. It still uses your Codex login.

Both run from the same empty folder every time, so repeated questions can reuse the prompt cache.

**Free and paid Codex accounts both work:** when you pick Codex, the server checks which models your account can run
by sending each listed model a tiny "Reply OK" prompt in the background (5–30 seconds). A free account then only sees
the models it can use (like Luna); a paid plan also sees Sol, Terra and Astra. "Default" means the best model your
account can run. The result is saved in `site/codex_models.local.json` (ignored by git) and checked again when the
account, route or model list changes. Press **Scan again** on the Settings page after upgrading your plan.

To use as little of your plan as possible, pick a small model (Haiku, Luna) with **Low** effort.

The server only listens on `127.0.0.1` (your computer), so nobody else on your network can use it.

## Troubleshooting

- **Port 8000 is already in use:** another copy is probably still running. Close it, or change `PORT` in `site/server.py`.
- **"The local server is not running":** you opened the HTML file directly. Start the server and use http://localhost:8000/site/.
- **AI says the CLI was not found:** run `claude --version` or `codex --version` in a new terminal. If that works,
  restart the site.
- **Codex says a model "is not supported":** pick another model, or "Default", under Settings.
- **`py` is not recognized (Windows):** reinstall Python from python.org and tick "Add python.exe to PATH", or edit
  `site\start.bat` to use `python` instead of `py`.

## Project layout

| Path | What it is |
|---|---|
| `site/*.html` | The pages: home, practice, learn, plan, progress, notes, settings |
| `site/js/` | Page code; `problems.js` and `lessons.js` are generated by `site/tools/` |
| `site/server.py` | Local server: pages, saving (`/api/sync`), settings, AI (`/api/ai`) |
| `site/notes_store.py` | Writes your work to the save folder and builds the progress analytics |
| `site/mistakes.py` | Sorts failed runs into kinds of mistakes |
| `site/vendor/three/` | The parts of three.js (MIT license) used for the 3D graphics |
| `site/test/grade.test.mjs` | Grader tests: `node site/test/grade.test.mjs` |
