@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

if not exist ".env" (
    echo Creating .env from .env.example...
    copy .env.example .env
)

echo.
echo Starting NEXORA on http://localhost:4000
echo Swagger docs: http://localhost:4000/docs
echo.
uvicorn app.main:app --host 0.0.0.0 --port 4000
