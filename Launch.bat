@echo off
setlocal
cd /d "%~dp0"

title xToys Library Manager

echo ================================================
echo          xToys Library Manager
echo ================================================
echo.

if exist ".venv\Scripts\python.exe" (
    echo Starting with project virtual environment...
    echo.
    ".venv\Scripts\python.exe" main.py
    goto finished
)

where python >nul 2>nul
if %errorlevel%==0 (
    echo Starting with Python...
    echo.
    python main.py
    goto finished
)

where py >nul 2>nul
if %errorlevel%==0 (
    echo Starting with Python Launcher...
    echo.
    py -3 main.py
    goto finished
)

echo.
echo ERROR: Python could not be found.
echo.
echo Install Python 3 and make sure it is available on PATH.

:finished
echo.
if errorlevel 1 (
    echo The program exited with an error.
) else (
    echo The program has closed.
)
echo.
pause
endlocal
