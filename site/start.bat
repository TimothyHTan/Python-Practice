@echo off
cd /d "%~dp0.."
start "" http://localhost:8000/site/
py site\server.py
