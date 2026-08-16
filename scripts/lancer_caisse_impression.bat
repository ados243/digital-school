@echo off
REM Digital School — poste caisse : impression sans boite de dialogue
REM Les 2 exemplaires partent sur l'imprimante Windows par defaut (format du pilote).
REM Usage : double-clic, ou : lancer_caisse_impression.bat http://127.0.0.1:8000/

setlocal
set "APP_URL=http://127.0.0.1:8000/finances/paiements/nouveau/"
if not "%~1"=="" set "APP_URL=%~1"

set "BROWSER="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "BROWSER=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "BROWSER=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "BROWSER=%LocalAppData%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "BROWSER=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not defined BROWSER if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "BROWSER=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"

if not defined BROWSER (
  echo Chrome ou Edge introuvable. Installez Google Chrome, puis relancez ce script.
  pause
  exit /b 1
)

echo Lancement caisse Digital School (impression silencieuse)...
echo URL : %APP_URL%
echo Imprimante utilisee : celle definie par defaut dans Windows.
echo.
start "" "%BROWSER%" --kiosk-printing --new-window "%APP_URL%"
endlocal
