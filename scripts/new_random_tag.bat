@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "CHARS=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
set "TAG=v"

for /L %%i in (1,1,6) do (
  set /A "IDX=!RANDOM! %% 36"
  for %%c in (!IDX!) do set "TAG=!TAG!!CHARS:~%%c,1!"
)

echo New tag: %TAG%
set /P TITLE=Release title:
set /P DESC=Release description (single line):
echo.
echo Summary:
echo Tag: %TAG%
echo Title: %TITLE%
echo Description: %DESC%
echo.
set /P CONFIRM=Create and push this tag? (y/N):
if /I not "%CONFIRM%"=="Y" (
  echo Aborted.
  exit /B 1
)

git tag %TAG%
if errorlevel 1 exit /B 1
git push --tags
if errorlevel 1 exit /B 1

echo Created and pushed tag: %TAG%
