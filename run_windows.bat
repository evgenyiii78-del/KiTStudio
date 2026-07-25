@echo off
cd /d %~dp0
if not exist .env copy .env.example .env
if not exist .venv py -3.12 -m venv .venv
call .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m app.main
pause
