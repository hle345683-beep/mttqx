@echo off
cd /d "%~dp0"
start "" "http://127.0.0.1:3000"
node start_demo.js
pause
