@echo off
echo 🔄 Launching DCS servers and Discord bot...

:: Start all DCS instances and sanitize MissionScripting.lua
powershell.exe -ExecutionPolicy Bypass -File "C:\DCSAdminBot\Scripts\DCSManage.ps1" -Action start

:: Start the Python Discord bot
python "C:\DCSAdminBot\DCS_admin_bot.py"
