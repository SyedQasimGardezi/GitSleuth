@echo off
echo Installing GitSleuth dependencies...
echo.

echo Installing Python dependencies...
cd backend
pip install -r requirements.txt
cd ..

echo.
echo Installing Node.js dependencies...
cd frontend
npm install
cd ..

echo.
echo Dependencies installed successfully!
echo.
echo To start the application:
echo 1. Run start_backend.bat in one terminal
echo 2. Run start_frontend.bat in another terminal
echo 3. Open http://localhost:3000 in your browser
echo.

pause
