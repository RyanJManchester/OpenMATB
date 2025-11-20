@echo off
setlocal

REM Make everything relative to this .bat
@REM cd /d "%~dp0"

set "HTML=pvtb_touch_autosave.html"
set "FIREFOX=C:\Program Files\Mozilla Firefox\firefox.exe"

REM 1) FIRST PVT (baseline response test)
"%FIREFOX%" "%CD%\%HTML%"

REM 2) Wait for all Firefox processes to exit
echo Waiting for Firefox to close (PVT 1)...
:wait_for_firefox1
timeout /t 1 /nobreak >nul
tasklist /FI "IMAGENAME eq firefox.exe" | find /I "firefox.exe" >nul
if not errorlevel 1 goto wait_for_firefox1

REM 3) MAIN TASK / FATIGUE INDUCTION BLOCK (Python "start")
cd start
py -3.9 main.py
cd ..

REM 4) SECOND PVT (repeat response test)
"%FIREFOX%" "%CD%\%HTML%"

REM 5) Wait for all Firefox processes to exit
echo Waiting for Firefox to close (PVT 2)...
:wait_for_firefox2
timeout /t 1 /nobreak >nul
tasklist /FI "IMAGENAME eq firefox.exe" | find /I "firefox.exe" >nul
if not errorlevel 1 goto wait_for_firefox2

REM 6) FINAL CLEANUP / END BLOCK (Python "end")
cd end
py -3.9 main.py
cd ..

endlocal
