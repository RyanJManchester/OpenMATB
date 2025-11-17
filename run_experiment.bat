@echo off
setlocal

REM Make everything relative to the folder this .bat file is in
cd /d "%~dp0"

REM 1) cd start/
cd start

REM 2) py -3.9 .\main.py
py -3.9 main.py

REM 3) cd ..
cd ..

REM 4) Open "pvt_autosave.html" in Firefox and wait for it to close
set "HTML=pvtb_touch_autosave.html"

if not exist "%HTML%" (
    echo File "%HTML%" not found in %CD%.
    pause
    goto :EOF
)

REM If firefox is on PATH, this works:
start "" /wait firefox "%CD%\%HTML%"

REM If that doesn't work, comment the line above and uncomment this,
REM adjusting the path to firefox.exe as needed:
REM start "" /wait "C:\Program Files\Mozilla Firefox\firefox.exe" "%CD%\%HTML%"

REM 5) cd end/
cd end

REM 6) py -3.9 .\main.py
py -3.9 main.py

cd ..
REM 4) Open "pvt_autosave.html" in Firefox and wait for it to close
set "HTML=pvtb_touch_autosave.html"

if not exist "%HTML%" (
    echo File "%HTML%" not found in %CD%.
    pause
    goto :EOF
)
REM If firefox is on PATH, this works:
start "" /wait firefox "%CD%\%HTML%"


endlocal
