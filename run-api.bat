@echo off
set PYTHONPATH=
cd /d C:/Users/jacke/Downloads/smartbiz-mvp
.venv\Scripts\python.exe -m uvicorn smartbiz.main:app --host 0.0.0.0 --port 8000
pause
