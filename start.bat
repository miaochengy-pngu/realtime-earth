@echo off
REM ============================================================================
REM Realtime Earth — Windows 启动器 (双击即可运行)
REM 委托给跨平台的 start.py，它会处理 venv、依赖安装、端口清理、启动 uvicorn
REM ============================================================================
setlocal

echo.
echo ==========================================================
echo   Realtime Earth - Starting up...
echo ==========================================================
echo.

REM 优先尝试 py launcher (Windows 推荐)，回退到 python
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py -3 "%~dp0start.py" %*
    goto :end
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    python "%~dp0start.py" %*
    goto :end
)

echo.
echo [ERROR] Python not found on PATH.
echo.
echo Please install Python 3.11+ from:
echo     https://www.python.org/downloads/
echo.
echo During installation, MAKE SURE to check
echo "Add Python to PATH" at the bottom of the installer.
echo.
pause
exit /b 1

:end
echo.
echo Press any key to close this window...
pause >nul
endlocal
