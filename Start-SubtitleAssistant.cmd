@echo off
setlocal
pushd "%~dp0"
python -m subtitle_translator.tool gui %*
set "subtitle_exit=%ERRORLEVEL%"
popd
exit /b %subtitle_exit%
