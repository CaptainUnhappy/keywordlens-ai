
@echo off
echo Starting KeywordLens AI System...

:: Check for .env file
if not exist ".env" (
    echo.
    echo [ERROR] .env file not found!
    echo Please ensure .env exists in the root directory.
    pause
    exit /b
)

echo.
echo [Checking Backend Environment...]
where uv >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo uv not found. Installing...
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
)

echo Syncing Python dependencies...
uv sync

echo.
echo [Checking Frontend Environment...]
if not exist "node_modules" (
    echo node_modules not found. Installing dependencies...
    call npm install
)

echo.
echo [1/2] Starting Python Backend...
start "Python Backend" /D "amazon-keyword-filter" uv run python server.py

echo.
echo [2/2] Starting React Frontend...
start "React Frontend" npm run dev

echo.
echo System Started!
