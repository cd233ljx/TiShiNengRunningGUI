@echo off
setlocal

cd /d "%~dp0\.."

if not exist .venv\Scripts\python.exe (
  echo [ERROR] .venv not found. 请先 python -m venv .venv 并安装依赖。
  exit /b 1
)

call .venv\Scripts\activate.bat

echo === clean runtime test DB ===
if exist tsn_data.db del /f /q tsn_data.db
if exist tsn_data.db-journal del /f /q tsn_data.db-journal

echo === pytest ===
python -m pytest tests\ -q
if errorlevel 1 (
  echo [ERROR] tests failed
  exit /b 2
)

echo === PyInstaller ===
python -m PyInstaller tishineng.spec --clean --noconfirm
if errorlevel 1 (
  echo [ERROR] PyInstaller failed
  exit /b 3
)

if not exist dist\TiShiNeng.exe (
  echo [ERROR] dist\TiShiNeng.exe missing
  exit /b 4
)

echo.
echo === Build OK ===
echo Run dist\TiShiNeng.exe and follow docs\packaging-smoke.md
endlocal
