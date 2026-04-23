@echo off
chcp 65001 >nul
echo ========================================
echo   Smiger AI Pre-sales Bot - Startup
echo ========================================
echo.

cd /d "%~dp0"

:: Create .env from template if it doesn't exist
if not exist ".env" (
    echo [1/3] Creating .env from .env.example ...
    copy .env.example .env >nul
    echo       Done. Edit .env if you need to change API keys.
) else (
    echo [1/3] .env already exists, skipping.
)

echo.
echo [2/3] Building and starting all services ...
echo       This may take a few minutes on first run.
echo.

docker compose up -d --build

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Docker Compose failed. Make sure Docker Desktop is running.
    pause
    exit /b 1
)

echo.
echo [3/3] Waiting for services to be ready ...
timeout /t 8 /nobreak >nul

echo.
echo ========================================
echo   All services are running!
echo ========================================
echo.
echo   Chat UI:     http://localhost:3000
echo   Admin Panel: http://localhost:3000/admin
echo   API Docs:    http://localhost:8000/docs
echo   Health:      http://localhost:8000/api/health
echo.
echo   Admin login: admin / smiger2026
echo.
echo   To load seed data (first time only):
echo     docker compose exec backend python -m app.seed
echo.
echo   To stop:  docker compose down
echo   To logs:  docker compose logs -f
echo ========================================
pause
