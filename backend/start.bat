@echo off
echo Starting Placement Portal Backend...
echo.

REM Use the correct Python path
set PYTHON_PATH=C:\Users\sharm\AppData\Local\Programs\Python\Python312\python.exe

REM Check if virtual environment exists, if not, use system Python
if exist "venv_win\Scripts\activate.bat" (
    echo Using virtual environment...
    call venv_win\Scripts\activate.bat
    python run.py
) else (
    echo Using system Python...
    %PYTHON_PATH% run.py
)

pause
