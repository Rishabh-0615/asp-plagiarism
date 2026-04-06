@echo off
REM ASP Plagiarism Service Startup Script

echo Starting ASP Plagiarism Service...
echo.

REM Check if venv exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate venv
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/upgrade dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Start Flask app
echo.
echo ============================================
echo Starting Flask server on port 5000...
echo ============================================
echo.
echo API will be available at:
echo http://localhost:5000
echo.
echo Health check: http://localhost:5000/api/v1/detect/health
echo.

python app.py

pause
