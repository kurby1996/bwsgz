@echo off
chcp 65001 >nul
cd /d "%~dp0"
start "" "blastem-兼容模式\blastem.exe" -r J -g "roms\三國志II-霸王三国志.md"
