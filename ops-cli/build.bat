@echo off
REM Build ops-cli executable for Windows
REM Requires: pip install pyinstaller

echo Building ops-cli...

cd /d "%~dp0"

REM Install build dependencies
pip install pyinstaller paramiko cryptography pyyaml jinja2 packaging -q

REM Build
pyinstaller ops-cli.spec --clean

echo.
echo Build complete! Executable is in:
echo   dist\ops-cli.exe
echo.
echo To distribute:
echo   1. Copy dist\ops-cli.exe to target machine
echo   2. User needs only to run it (no Python required)
echo.
pause