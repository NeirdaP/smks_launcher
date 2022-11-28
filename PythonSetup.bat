echo ---------------------
echo --- PYTHON SETUP ----
echo ---------------------

if '%SMKS_STUDIO_ROOT%'=='' (set SMKS_STUDIO_ROOT=P:\DEV\dev\smks_studio)
if '%PYTHONDIR%'=='' (set PYTHONDIR=I:\bin\Python3KBR)

cd /D %PYTHONDIR%

%PYTHONDIR%\python -m pip install virtualenv
%PYTHONDIR%\python -m virtualenv smks_env
%PYTHONDIR%\python -m virtualenv maya_env

echo Update Smks Env

pushd %PYTHONDIR%\smks_env
cd /D %PYTHONDIR%\smks_env
call Scripts\activate.bat
python -m pip install --index-url="I:\python_packages\dists" --extra-index-url="https://pypi.org/simple" -U -r %SMKS_STUDIO_ROOT%\requirements.txt
if %ErrorLevel% equ 1 (
    echo ERROR: INSTALL FAILED
    exit 1
)

echo %PYTHONDIR%|find "3" >nul
if %ErrorLevel% equ 1 (
    echo "Python 2 ?"
) else (
    python -m pip install--find-links="I:\python_packages\dists" PySide2==5.15.0
)

call Scripts\deactivate.bat
popd

echo ---------------
echo Update Maya Env

pushd %PYTHONDIR%\maya_env
cd /D %PYTHONDIR%\maya_env
call Scripts\activate.bat
python -m pip install --index-url="I:\python_packages\dists" --extra-index-url="https://pypi.org/simple" -U -r %~2

if %ErrorLevel% equ 1 (
    echo ERROR: INSTALL FAILED
    exit 1
)

call Scripts\deactivate.bat
popd

echo Update Ended !
echo.
