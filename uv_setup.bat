@echo off
echo Installing uv...
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

echo Initializing environment...
uv sync

echo Setup complete!
pause
