@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Build xToys Library Manager

echo ============================================================
echo       xToys Library Manager - Standalone Windows Build
echo ============================================================
echo.
set "PYTHON="
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
if not defined PYTHON ( where python >nul 2>nul & if not errorlevel 1 set "PYTHON=python" )
if not defined PYTHON ( where py >nul 2>nul & if not errorlevel 1 set "PYTHON=py -3" )
if not defined PYTHON (
  echo ERROR: Python 3 could not be found.
  pause
  exit /b 1
)
echo Python: %PYTHON%
echo.
echo [1/5] Installing build dependencies...
%PYTHON% -m pip install --upgrade pip || goto :failed
%PYTHON% -m pip install pyinstaller playwright pillow || goto :failed

echo.
echo [2/5] Installing Playwright Chromium...
%PYTHON% -m playwright install chromium || goto :failed

echo.
echo [3/5] Building standalone EXE...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
%PYTHON% -m PyInstaller --noconfirm --clean xToysLibrary.spec || goto :failed
if not exist "dist\xToys Library Manager.exe" goto :failed

echo.
echo [4/5] Installing EXE into project root...
copy /y "dist\xToys Library Manager.exe" ".\xToys Library Manager.exe" >nul || goto :failed

echo.
echo [5/5] Copying Playwright browsers beside the project...
if exist "playwright-browsers" rmdir /s /q "playwright-browsers"
mkdir "playwright-browsers"
set "BROWSER_ROOT=%LOCALAPPDATA%\ms-playwright"
if not exist "%BROWSER_ROOT%" goto :browser_missing
for /d %%D in ("%BROWSER_ROOT%\chromium-*") do xcopy /e /i /y "%%~D" "playwright-browsers\%%~nxD" >nul
for /d %%D in ("%BROWSER_ROOT%\chromium_headless_shell-*") do xcopy /e /i /y "%%~D" "playwright-browsers\%%~nxD" >nul
for /d %%D in ("%BROWSER_ROOT%\ffmpeg-*") do xcopy /e /i /y "%%~D" "playwright-browsers\%%~nxD" >nul
goto :success
:browser_missing
echo WARNING: Playwright browser files were not found.
:success
echo.
echo ============================================================
echo BUILD COMPLETE
echo ============================================================
echo.
echo Double-click "xToys Library Manager.exe" to launch the GUI.
echo Keep it in this project folder so GitHub publishing can use .git.
echo.
pause
endlocal
exit /b 0
:failed
echo.
echo BUILD FAILED.
pause
endlocal
exit /b 1
