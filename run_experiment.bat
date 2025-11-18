@echo off
setlocal

REM Make everything relative to the folder this .bat file is in
cd /d "%~dp0"

set "HTML=pvtb_touch_autosave.html"+
@REM "C:\Program Files\Mozilla Firefox\firefox.exe" "%CD%\%HTML%"

@REM DEMO

cd start
py -3.9 main.py



@REM record 5 minute rest 
@REM record subjective measures

REM 4) Open PVT
cd ..
"C:\Program Files\Mozilla Firefox\firefox.exe" "%CD%\%HTML%"


@REM Fatigue induction
cd end
py -3.9 main.py


@REM record 5 minute rest 
@REM record subjective measures

REM 4) Open PVT
cd ..
"C:\Program Files\Mozilla Firefox\firefox.exe" "%CD%\%HTML%"

endlocal
