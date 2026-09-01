@echo off
REM Email MCP Server Launcher
REM Uses %~dp0 so this works from any checkout location.
cd /d "%~dp0"

REM Prefer the project venv interpreter (dependencies are installed in .venv)
set "PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo [ERROR] Virtual environment interpreter not found:
    echo   %PYTHON%
    echo Please run "uv sync" first.
    pause
    exit /b 1
)

REM The server can start without .env; the agent may configure it later.
if not exist ".env" (
    echo [WARN] .env not found; starting unconfigured.
    echo        An agent can run get_account_status / configure_account.
)

echo Starting Email MCP Server...
echo URL: http://127.0.0.1:8080
echo Press Ctrl+C to stop
echo.

"%PYTHON%" -m email_mcp.server --http --host 127.0.0.1 --port 8080

pause
