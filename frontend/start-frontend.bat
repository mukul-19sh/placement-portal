@echo off
echo Starting Frontend HTTP Server...
echo.
echo Opening http://localhost:3000
.
cd %~dp0

REM Check if Python is available
python -c "import http.server" 2>nul
if errorlevel 1 (
    echo Python not found. Please install Python first.
    pause
    exit /b 1
)

REM Start HTTP server on port 3000
start http://localhost:3000
python -m http.server 3000

pause
