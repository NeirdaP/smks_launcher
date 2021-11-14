echo ---------------------
echo ---- SMKS STUDIO ----
echo ---------------------
echo.

if '%SMKS_STUDIO_ROOT%'=='' (set SMKS_STUDIO_ROOT=P:\DEV\dev\smks_studio)
set PYTHONPATH=%SMKS_STUDIO_ROOT%\smks_studio_home\python

call %PYTHONDIR%\smks_env\Scripts\activate
python -c "import smks_studio.gui.app as smks_gui;smks_gui.run_session(*smks_gui.configuration_from_preset('%CONFIG%'))"
EXIT %ERRORLEVEL%
