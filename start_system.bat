@echo off
echo Starting Visitor Management System...

echo Starting Backend Server...
start cmd /k "cd /d %~dp0 && python backend.py"

echo Starting Security App...
start cmd /k "cd /d %~dp0 && python security_app.py"

echo Starting Host Confirmation Interface...
start cmd /k "cd /d %~dp0 && python host_confirmation.py"

echo.
echo All services started!
echo Backend: http://localhost:5000
echo Security App: http://localhost:5001/security
echo Host Confirmation: http://localhost:5002
echo.
echo Press any key to exit...
pause >nul