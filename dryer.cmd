@echo off
setlocal
set "DRYER_ROOT=%~dp0"
set "DRYER_PYTHON=%DRYER_ROOT%.venv\Scripts\python.exe"

if not exist "%DRYER_PYTHON%" (
    where py >nul 2>nul
    if errorlevel 1 (
        python -m venv "%DRYER_ROOT%.venv"
    ) else (
        py -3 -m venv "%DRYER_ROOT%.venv"
    )
    if errorlevel 1 exit /b 1
)

if not exist "%DRYER_ROOT%.venv\Scripts\dryer.exe" (
    "%DRYER_PYTHON%" -m pip install -e "%DRYER_ROOT%." 1>&2
    if errorlevel 1 exit /b 1
)

"%DRYER_PYTHON%" -m dryer %*
exit /b %errorlevel%
