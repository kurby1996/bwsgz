@echo off
chcp 65001 >nul
cd /d "%~dp0"
where pythonw >nul 2>nul
if not errorlevel 1 (
    start "" pythonw -m trainer.app
    exit /b
)
where python >nul 2>nul
if not errorlevel 1 (
    python -m trainer.app
    exit /b
)
echo 请安装 Python 3.10 或以上版本，包含 tkinter 组件。
pause
