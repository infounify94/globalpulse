@echo off
echo Starting GlobalPulse Prediction API...
echo.

:: Use local SQLite DB (has 1.4GB of real historical data)
:: This avoids the Supabase DNS error on home network
set GLOBALPULSE_DB_URL=sqlite:///globalpulse_dev.db

:: Load other keys from .env
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if not "%%a"=="" if not "%%b"=="" set %%a=%%b
)

:: Override DB URL to keep local SQLite
set GLOBALPULSE_DB_URL=sqlite:///globalpulse_dev.db

echo Using database: %GLOBALPULSE_DB_URL%
echo.

:: Install required packages
echo Installing dependencies...
pip install fastapi uvicorn sqlalchemy joblib numpy pandas scikit-learn xgboost python-dotenv

:: Run FastAPI
echo.
echo Starting server on http://127.0.0.1:8000 ...
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload

pause
