@echo off
cd /d "%~dp0"
python -m qbc_workbench.cli serve --host 127.0.0.1 --port 8765
