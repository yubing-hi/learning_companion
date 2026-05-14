@echo off
setlocal

set HOST=127.0.0.1
set PORT=8000

cd /d "%~dp0"

if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        if not "%%A"=="" if not "%%A:~0,1"=="#" set "%%A=%%B"
    )
)

echo Starting Learning Assistant...
echo.
echo Browser address: http://%HOST%:%PORT%/
echo Close this window to stop the service.
echo.

start "" "http://%HOST%:%PORT%/"

where py >nul 2>nul
if %errorlevel%==0 (
    py -m uvicorn app.main:app --host %HOST% --port %PORT%
    goto :eof
)

python -m uvicorn app.main:app --host %HOST% --port %PORT%
