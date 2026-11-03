@echo off
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe run.py --demo
  goto done
)
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
  "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" run.py --demo
  goto done
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 run.py --demo
  goto done
)
python run.py --demo
:done
if errorlevel 1 goto fail
pause
exit /b
:fail
echo Could not start. Install Python 3.10+ or follow README.md.
pause
