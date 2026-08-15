@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul && python main.py && goto end
where py >nul 2>nul && py -3 main.py && goto end
echo Python was not found.
pause
:end
endlocal
