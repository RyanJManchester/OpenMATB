@echo off
setlocal

REM Make everything relative to this .bat
@REM cd /d "%~dp0"

set "HTML=pvtb_touch_autosave.html"
set "FIREFOX=C:\Program Files\Mozilla Firefox\firefox.exe"


REM 3) Now run Python
cd start
py -3.9 main.py
cd ..


REM 1) Open Firefox with your HTML
"%FIREFOX%" "%CD%\%HTML%"

REM 2) Wait for all Firefox processes to exit
echo Waiting for Firefox to close...
:wait_for_firefox1
timeout /t 1 /nobreak >nul
tasklist /FI "IMAGENAME eq firefox.exe" | find /I "firefox.exe" >nul
if not errorlevel 1 goto wait_for_firefox1

REM 3) Now run Python
cd end
py -3.9 main.py
cd ..


REM 1) Open Firefox with your HTML
"%FIREFOX%" "%CD%\%HTML%"

REM 2) Wait for all Firefox processes to exit
echo Waiting for Firefox to close...
:wait_for_firefox2
timeout /t 1 /nobreak >nul
tasklist /FI "IMAGENAME eq firefox.exe" | find /I "firefox.exe" >nul
if not errorlevel 1 goto wait_for_firefox2

endlocal
