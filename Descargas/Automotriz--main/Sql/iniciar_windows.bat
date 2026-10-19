@echo off
cd /d "%~dp0"
echo Abre http://localhost:8000/index.html en tu navegador.
py -3 servidor.py
pause
