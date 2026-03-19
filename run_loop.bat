@echo off
REM Start backend if not already running
echo Starting backend...
start /B python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

REM Wait for backend to start
timeout /t 5 /nobreak

REM Run the loop test
echo.
echo Running loop diagnostic and test...
python quick_test_and_loop.py
pause
