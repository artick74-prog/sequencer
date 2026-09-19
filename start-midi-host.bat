@echo off
cd /d "%~dp0"
python scripts\local_server.py --open
echo.
echo Server stopped. Press any key to close this window.
pause >nul
