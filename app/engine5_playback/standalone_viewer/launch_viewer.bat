@echo off
setlocal
echo ===============================================================================
echo   TRI-NETRA DFIR -- PORTABLE COURT EVIDENCE VIEWER (STANDALONE)
echo   Original Stream Playback -- In-Memory Bitstream Decoding -- Zero Re-Encoding
echo ===============================================================================
echo.

cd /d "%~dp0"

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python trinetra_viewer.py %*
    goto :end
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 trinetra_viewer.py %*
    goto :end
)

echo [ERROR] Python is not installed or not in PATH.
echo Please install Python 3.10+ and run: pip install -r requirements.txt
pause

:end
endlocal
