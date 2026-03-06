@echo off
REM AI Employee System Startup Script
REM Opens 7 separate Command Prompt windows for each service

cd /d F:\AI_Employee_Vault

echo Starting AI Employee System...
echo.
echo Opening 7 service windows...
echo.

REM Window 1: Gmail Watcher
start "AI Employee - Gmail Watcher" cmd /k "cd /d F:\AI_Employee_Vault && python gmail_watcher.py"

REM Window 2: File Watcher
start "AI Employee - File Watcher" cmd /k "cd /d F:\AI_Employee_Vault && python file_watcher.py"

REM Window 3: HITL Monitor
start "AI Employee - HITL Monitor" cmd /k "cd /d F:\AI_Employee_Vault && python hitl_monitor.py"

REM Window 4: Master Scheduler
start "AI Employee - Master Scheduler" cmd /k "cd /d F:\AI_Employee_Vault && python master_scheduler.py"

REM Window 5: WhatsApp Watcher
start "AI Employee - WhatsApp Watcher" cmd /k "cd /d F:\AI_Employee_Vault && python whatsapp_watcher.py"

REM Window 6: Twitter Scheduler
start "AI Employee - Twitter Scheduler" cmd /k "cd /d F:\AI_Employee_Vault && python twitter_scheduler.py"

REM Window 7: Instagram Scheduler
start "AI Employee - Instagram Scheduler" cmd /k "cd /d F:\AI_Employee_Vault && python instagram_scheduler.py"

echo.
echo All 7 services started!
echo.
echo Services running:
echo   1. Gmail Watcher - Monitoring Gmail for new emails
echo   2. File Watcher - Monitoring file system for changes
echo   3. HITL Monitor - Processing human approvals
echo   4. Master Scheduler - Running scheduled tasks
echo   5. WhatsApp Watcher - Monitoring WhatsApp Web for messages
echo   6. Twitter Scheduler - Auto-posting tweets every 12 hours
echo   7. Instagram Scheduler - Auto-posting on Instagram every 24 hours
echo.
echo Close any window to stop that specific service.
echo.
pause
