@echo off
echo ===================================
echo DIAGNOSTIC: Checking Placement Portal
echo ===================================
echo.

echo [1/5] Checking Python installation...
python --version
if errorlevel 1 (
    echo FAILED: Python not found!
    goto error
)
echo SUCCESS: Python found
echo.

echo [2/5] Checking Backend Folder...
cd /d "%~dp0\backend" 2>nul
if errorlevel 1 (
    echo FAILED: Cannot find backend folder at %~dp0\backend
    goto error
)
echo SUCCESS: Backend folder found at %CD%
echo.

echo [3/5] Testing Backend Import...
python -c "import app.main; print('Import successful')" 2>&1
if errorlevel 1 (
    echo FAILED: Cannot import app.main module
    echo Installing dependencies...
    pip install -r requirements.txt
    echo Trying again...
    python -c "import app.main; print('Import successful')" 2>&1
    if errorlevel 1 (
        echo STILL FAILED: There may be a code error
        goto error
    )
)
echo SUCCESS: Backend module imports correctly
echo.

echo [4/5] Checking if port 8000 is available...
netstat -an | find "8000" | find "LISTENING" >nul
if errorlevel 1 (
    echo SUCCESS: Port 8000 is available
) else (
    echo WARNING: Port 8000 is already in use!
    echo You may need to close another running instance.
)
echo.

echo [5/5] Checking Frontend Folder...
cd /d "%~dp0\frontend" 2>nul
if errorlevel 1 (
    echo FAILED: Cannot find frontend folder
    goto error
)
echo SUCCESS: Frontend folder found
echo.

echo ===================================
echo All checks passed!
echo.
echo Now you can run start-all.bat to start both servers
echo ===================================
goto end

:error
echo.
echo ===================================
echo DIAGNOSTIC FAILED
echo ===================================
echo.
echo Please check the errors above and fix them.
echo Common issues:
echo - Python not installed: Install from python.org
echo - Dependencies missing: Run 'pip install -r requirements.txt'
echo - Port 8000 in use: Close other applications using that port
echo.

:end
pause
