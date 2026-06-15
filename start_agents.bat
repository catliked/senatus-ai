@echo off
title Senatus AI — Startup
echo.
echo  ███████╗███████╗███╗   ██╗ █████╗ ████████╗██╗   ██╗███████╗
echo  ██╔════╝██╔════╝████╗  ██║██╔══██╗╚══██╔══╝██║   ██║██╔════╝
echo  ███████╗█████╗  ██╔██╗ ██║███████║   ██║   ██║   ██║███████╗
echo  ╚════██║██╔══╝  ██║╚██╗██║██╔══██║   ██║   ██║   ██║╚════██║
echo  ███████║███████╗██║ ╚████║██║  ██║   ██║   ╚██████╔╝███████║
echo  ╚══════╝╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚══════╝
echo.
echo  Enterprise Investment Committee Platform
echo  ==========================================
echo.

set PYPATH=C:\Users\DELL\AppData\Local\Python\pythoncore-3.14-64\python.exe
set DIR=%~dp0

echo  [1/6] Starting ResearchAgent...
start "ResearchAgent" cmd /k "cd /d %DIR% && %PYPATH% agents\research_agent.py"
timeout /t 1 /nobreak >nul

echo  [2/6] Starting BullAnalyst...
start "BullAnalyst" cmd /k "cd /d %DIR% && %PYPATH% agents\bull_agent.py"
timeout /t 1 /nobreak >nul

echo  [3/6] Starting BearAnalyst...
start "BearAnalyst" cmd /k "cd /d %DIR% && %PYPATH% agents\bear_agent.py"
timeout /t 1 /nobreak >nul

echo  [4/6] Starting ComplianceOfficer...
start "ComplianceOfficer" cmd /k "cd /d %DIR% && %PYPATH% agents\compliance_agent.py"
timeout /t 1 /nobreak >nul

echo  [5/6] Starting SynthesisChair...
start "SynthesisChair" cmd /k "cd /d %DIR% && %PYPATH% agents\synthesis_agent.py"
timeout /t 2 /nobreak >nul

echo  [6/6] Starting Web Server...
start "Senatus Web Server" cmd /k "cd /d %DIR% && %PYPATH% -m uvicorn main:app --reload --port 8000"
timeout /t 3 /nobreak >nul

echo.
echo  ==========================================
echo   All 6 services started!
echo.
echo   Dashboard:  http://localhost:8000
echo   Band Room:  https://app.band.ai
echo.
echo   Press any key to open the dashboard...
pause >nul
start http://localhost:8000
