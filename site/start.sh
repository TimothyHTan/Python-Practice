#!/usr/bin/env sh
# Starts the practice site on Linux (or macOS) and opens http://localhost:8000/site/
cd "$(dirname "$0")/.." || exit 1
(sleep 1; xdg-open http://localhost:8000/site/ >/dev/null 2>&1 || open http://localhost:8000/site/ >/dev/null 2>&1) &
exec python3 site/server.py
