@echo off
REM Windows Task Scheduler Setup for AI Employee System
REM Creates a scheduled task to run startup.bat on Windows login

echo ============================================================
echo AI Employee System - Windows Task Scheduler Setup
echo ============================================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This script requires administrator privileges.
    echo Please right-click and select "Run as administrator".
    echo.
    pause
    exit /b 1
)

echo Running with administrator privileges...
echo.

REM Delete existing task if it exists
schtasks /Delete /TN "AI_Employee_Startup" /F >nul 2>&1
if %errorLevel% equ 0 (
    echo Removed existing AI_Employee_Startup task
)

REM Create new scheduled task
echo Creating scheduled task...
echo.

schtasks /Create /TN "AI_Employee_Startup" ^
    /TR "\"F:\AI_Employee_Vault\startup.bat\"" ^
    /SC ONLOGON ^
    /RU "%USERNAME%" ^
    /RL HIGHEST ^
    /F

if %errorLevel% equ 0 (
    echo.
    echo ============================================================
    echo SUCCESS! Scheduled task created successfully.
    echo ============================================================
    echo.
    echo Task Name: AI_Employee_Startup
    echo Trigger: On Windows Login
    echo Action: Run F:\AI_Employee_Vault\startup.bat
    echo.
    echo The AI Employee System will now start automatically when you log in.
    echo.
    echo To view or modify this task:
    echo   1. Open Task Scheduler (taskschd.msc)
    echo   2. Look for "AI_Employee_Startup" in the task list
    echo.
    echo To run the task manually:
    echo   schtasks /Run /TN "AI_Employee_Startup"
    echo.
    echo To delete the task:
    echo   schtasks /Delete /TN "AI_Employee_Startup"
    echo.
    echo ============================================================
) else (
    echo.
    echo ============================================================
    echo ERROR! Failed to create scheduled task.
    echo ============================================================
    echo.
    echo Please check:
    echo   1. You are running this script as Administrator
    echo   2. The file F:\AI_Employee_Vault\startup.bat exists
    echo   3. Python is installed and accessible
    echo.
)

pause
