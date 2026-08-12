@echo off
set "QBC_RUBY_ROOT=%~dp0tools\ruby\rubyinstaller-3.3.12-1-x64"
set "GEM_HOME=%~dp0tools\gems"
set "GEM_PATH=%GEM_HOME%"
"%QBC_RUBY_ROOT%\bin\ruby.exe" "%GEM_HOME%\bin\jekyll" %*

