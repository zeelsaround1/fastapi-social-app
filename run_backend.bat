@echo off
title FastSocial Backend
echo Starting FastSocial FastAPI Backend...
cd /d "%~dp0"
..\lang1\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pause

