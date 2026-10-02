@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Instale Python 3.12 ou superior, 64 bits, com a opcao Add Python to PATH.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if errorlevel 1 goto failure
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failure
".venv\Scripts\python.exe" -X utf8 scripts\doctor.py
if errorlevel 1 goto failure
start "" "http://127.0.0.1:8000"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
exit /b
:failure
echo Nao foi possivel iniciar. Consulte a mensagem acima.
pause
exit /b 1
