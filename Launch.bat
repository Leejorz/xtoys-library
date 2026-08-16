@echo off
setlocal
cd /d "%~dp0"
if exist "xToys Library Manager.exe" (
    start "xToys Library Manager" /d "%~dp0" "xToys Library Manager.exe"
    goto :end
)
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
    goto :end
)
where python >nul 2>nul
if %errorlevel%==0 (
    python main.py
    goto :end
)
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 main.py
    goto :end
)
msg * "xToys Library Manager: Python was not found and the standalone EXE is not installed."
:end
endlocal
