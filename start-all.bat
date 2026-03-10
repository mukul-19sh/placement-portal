@echo off
echo ===================================
echo Placement Portal - Quick Start
echo ===================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python from https://python.org
echo.
    pause
    exit /b 1
)

echo Python found: 
python --version
echo.

REM Check if backend folder exists
if not exist "%~dp0\backend" (
    echo ERROR: Backend folder not found!
    echo Make sure you're running this from the placement-portal folder.
    pause
    exit /b 1
)

REM Change to backend directory and start backend
echo [1/3] Starting Backend Server on http://localhost:8000...
cd /d "%~dp0\backend"

REM Test if we can import the app module
python -c "import app.main" >nul 2>&1
if errorlevel 1 (
    echo WARNING: Could not import app module. Installing dependencies...
    pip install -r requirements.txt
)

start "Backend Server" cmd /k "python run.py"

REM Wait for backend to start
echo [2/3] Waiting for backend to initialize (5 seconds)...
timeout /t 5 /nobreak >nul

REM Test if backend is actually running
echo Testing backend connection...
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo WARNING: Backend may not be responding yet. Waiting 3 more seconds...
    timeout /t 3 /nobreak >nul
) else (
    echo Backend is responding!
)

REM Change to frontend directory and start frontend
echo [3/3] Starting Frontend Server on http://localhost:3000...
cd /d "%~dp0\frontend"
start "Frontend Server" cmd /k "python -m http.server 3000"

REM Open browser
echo.
echo Opening browser...
start http://localhost:3000

echo.
echo ===================================
echo Both servers should be starting!
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo IMPORTANT: Access the site via http://localhost:3000
echo Do NOT open HTML files directly!
echo ===================================
echo.
echo If you see connection errors:
echo 1. Check the Backend Server window for errors
echo 2. Try refreshing the browser page
echo 3. Check that port 8000 is not blocked by firewall
echo ===================================

pause
