@echo off
cd /d "%~dp0"
py byd_spotify_patcher.py --gui
if errorlevel 1 pause
