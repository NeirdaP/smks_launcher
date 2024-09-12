if '%SMKS_STUDIO_ROOT%'=='' (set SMKS_STUDIO_ROOT=R:\supamonks\production\homemade_softwares\smks_studio)

cd /D %PYTHONDIR%

%PYTHONDIR%\python -m pip install virtualenv
%PYTHONDIR%\python -m virtualenv %~1

echo Update %~1

pushd %PYTHONDIR%\%~1
cd /D %PYTHONDIR%\%~1
call Scripts\activate.bat
python -m pip install --no-index --find-links="R:\third_party\python_packages\dists" -U -r %~2

if %ErrorLevel% equ 1 (
    echo ERROR: INSTALL FAILED
    exit 1
)

call Scripts\deactivate.bat
popd
