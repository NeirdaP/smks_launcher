IF EXIST %PYTHON2DIR% (
    IF NOT "%PYTHON2DIR:~0,2%"=="I:" (
        @RMDIR /Q /S %PYTHON2DIR%
    )
)

IF EXIST %PYTHON3DIR% (
    IF NOT "%PYTHON3DIR:~0,2%"=="I:" (
        @RMDIR /Q /S %PYTHON3DIR%
    )
)

setx PYTHONDIR I:\bin\Python3KBR
setx PYTHON2DIR I:\bin\PythonKBR
setx PYTHON3DIR I:\bin\Python3KBR
