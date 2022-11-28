if '%SMKS_STUDIO_ROOT%'=='' (set SMKS_STUDIO_ROOT=P:\DEV\dev\smks_studio)
if '%PYTHONDIR%'=='' (set PYTHONDIR=I:\bin\Python3KBR)

cd /D %PYTHONDIR%

%PYTHONDIR%\python -m pip install virtualenv
%PYTHONDIR%\python -m virtualenv %~1

echo Update %~1

pushd %PYTHONDIR%\%~1
cd /D %PYTHONDIR%\%~1
call Scripts\activate.bat
python -m pip install --index-url="I:\python_packages\dists" --extra-index-url="https://pypi.org/simple" -U -r %~2

if %ErrorLevel% equ 1 (
    echo ERROR: INSTALL FAILED
    exit 1
)

call Scripts\deactivate.bat
popd
