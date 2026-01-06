
@echo off
echo Starting KeywordLens AI System...

echo.
echo [1/2] Starting Python Backend...
start "Python Backend" /D "amazon-keyword-filter" uv run python server.py

echo.
echo [2/2] Starting React Frontend...
start "React Frontend" npm run dev

echo.
echo System Started!
