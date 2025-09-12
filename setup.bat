@echo off
echo Setting up GitSleuth...
echo.

echo Setting up Backend...
cd backend
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
cd ..

echo.
echo Setting up Frontend...
cd frontend
npm install
cd ..

echo.
echo Setup complete!
echo.
echo To start the application:
echo 1. Run start_backend.bat in one terminal
echo 2. Run start_frontend.bat in another terminal
echo 3. Open http://localhost:3000 in your browser
echo.
pause
