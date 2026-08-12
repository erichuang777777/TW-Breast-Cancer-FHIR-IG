@echo off
set "npm_config_cache=%~dp0..\.npm-cache"
"C:\Program Files\nodejs\node.exe" "%~dp0tools\node_modules\fsh-sushi\dist\app.js" %*
