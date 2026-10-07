@echo off
setlocal

rem ============================================================
rem  CS-BlackBook-Hub  dev launcher
rem  Double-click this file to start BOTH backend and frontend.
rem ============================================================

set "ROOT=%~dp0"

rem ---- Pre-flight checks ----
if not exist "%ROOT%backend\venv\Scripts\python.exe" (
    echo [ERROR] backend\venv not found.
    echo         First run once:  cd backend  ^&^&  python -m venv venv
    echo         then:            .\venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "%ROOT%frontend\node_modules" (
    echo [ERROR] frontend\node_modules not found.
    echo         First run once:  cd frontend  ^&^&  npm install
    pause
    exit /b 1
)

rem ---- Start backend (FastAPI, port 8000) in its own window ----
rem NOTE: do NOT add --reload here. On Windows, uvicorn's reload mode forces a
rem SelectorEventLoop, which does not support asyncio subprocess; the judge
rem sandbox (app/services/sandbox.py) needs asyncio.create_subprocess_exec.
echo [1/2] Starting backend  : http://localhost:8000
start "CS-BlackBook backend" /d "%ROOT%backend" cmd /k "venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

rem ---- Start frontend (Vite, port 5173) in its own window ----
echo [2/2] Starting frontend : http://localhost:5173
start "CS-BlackBook frontend" /d "%ROOT%frontend" cmd /k "npm run dev"

rem ---- Wait a moment, then open the browser ----
timeout /t 3 /nobreak >nul
start "" http://localhost:5173

echo.
echo Done. Close each console window to stop that service.
echo   Backend  API docs : http://localhost:8000/docs
echo   Frontend app      : http://localhost:5173
echo.
pause
endlocal
