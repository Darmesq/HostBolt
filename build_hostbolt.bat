@echo off
REM ============================================================
REM  HostBolt - build ca .exe portabil, cu icon si cerere UAC Administrator
REM  Pune in acelasi folder: HostBolt.py, HostBolt.ico, build_hostbolt.bat
REM ============================================================
cd /d "%~dp0"

if not exist HostBolt.ico (
  echo EROARE: lipseste HostBolt.ico langa script.
  pause & exit /b 1
)

echo [1/2] Instalez PyInstaller...
python -m pip install -U pyinstaller

echo [2/2] Construiesc HostBolt.exe...
python -m PyInstaller --noconfirm --onefile --windowed --uac-admin ^
  --name HostBolt --icon HostBolt.ico --add-data "HostBolt.ico;." ^
  HostBolt.py

echo.
echo Gata: %~dp0dist\HostBolt.exe
echo Daca in Explorer apare inca iconul vechi, e doar cache-ul Windows:
echo redenumeste exe-ul sau ruleaza:  ie4uinit.exe -show
pause
