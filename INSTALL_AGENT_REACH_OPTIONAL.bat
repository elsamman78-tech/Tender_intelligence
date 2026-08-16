@echo off
cd /d %~dp0
echo Agent-Reach is OPTIONAL. The core works without it.
echo This installs directly from the official GitHub repository, not the unrelated PyPI package.
if not exist .venv\Scripts\python.exe (echo Run INSTALL.bat first.& pause& exit /b 1)
call .venv\Scripts\activate.bat
pip install "git+https://github.com/Panniantong/Agent-Reach.git"
agent-reach doctor
pause
