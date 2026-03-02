@echo off
echo Opening Firefox to YouTube...
start "" "C:\Program Files\Mozilla Firefox\firefox.exe" "https://www.youtube.com"
echo.
echo Log in to YouTube if needed, then CLOSE Firefox completely.
echo This window will continue automatically once Firefox is closed.
echo.

:wait
timeout /t 2 /nobreak >nul
tasklist /fi "imagename eq firefox.exe" 2>nul | find /i "firefox.exe" >nul
if not errorlevel 1 goto wait

echo Firefox closed. Exporting cookies...
echo.
C:\Musicbot\venv\Scripts\yt-dlp.exe --cookies-from-browser firefox --cookies C:\Musicbot\cookies.txt --skip-download https://www.youtube.com/watch?v=dQw4w9WgXcQ

if errorlevel 1 (
    echo.
    echo ERROR: Cookie export failed. Make sure you were logged into YouTube in Firefox.
) else (
    echo.
    echo Done! Cookies saved to C:\Musicbot\cookies.txt
)
echo.
pause
