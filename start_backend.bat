@echo off
echo.
echo  =============================================
echo   Fearlessvest - Starting VERA Backend
echo  =============================================
echo.

cd /d "%~dp0backend"

:: Check if venv exists, create if not
if not exist "venv\Scripts\activate.bat" (
    echo  [1/3] Creating Python virtual environment...
    python -m venv venv
    echo  Done.
)

:: Activate venv
echo  [2/3] Activating virtual environment...
call venv\Scripts\activate.bat

:: Install/update dependencies
echo  [3/3] Installing dependencies...
pip install -r requirements.txt --quiet

echo.
echo  =============================================
echo   Backend starting at http://localhost:5000
echo   Open chatbot.html in your browser.
echo   Press Ctrl+C to stop the server.
echo  =============================================
echo.

:: Run Flask app
python app.py

pause
