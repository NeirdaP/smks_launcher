echo ---------------------
echo ---- SMKS STUDIO ----
echo ---------------------
echo.

if '%SMKS_STUDIO_ROOT%'=='' (set SMKS_STUDIO_ROOT=R:\supamonks\production\homemade_softwares\smks_studio)
set PYTHONPATH=%SMKS_STUDIO_ROOT%\smks_studio_home\python

call %PYTHONDIR%\smks_env\Scripts\activate
python -c "%SMKS_STUDIO_CMD%"
EXIT %ERRORLEVEL%
