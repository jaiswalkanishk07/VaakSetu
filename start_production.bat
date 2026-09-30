@echo off
echo ===================================================
echo     VaakSetu Production Orchestrator
echo ===================================================

echo [1/4] Starting Docker Infrastructure (Redis + Postgres)...
docker-compose up -d

echo [2/4] Starting FastAPI Backend (Production Mode)...
cd backend
start "VaakSetu Backend" cmd /c "python -m uvicorn task2_backend.main:app --host 0.0.0.0 --port 8000"

echo [3/4] Establishing Ngrok Tunnel for Twilio...
start "Ngrok Tunnel" cmd /c "python start_ngrok.py"

echo [4/4] Starting Next.js Frontend (Production Mode)...
cd ..\frontend
echo Please wait, starting optimized production build on port 3000...
npm run start

echo.
echo All services are running!
echo Frontend: http://localhost:3000
echo Backend:  http://localhost:8000
echo ===================================================
pause
