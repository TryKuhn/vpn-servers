@echo off
setlocal EnableDelayedExpansion

set SERVER=vpn@193.29.224.82
set SSH_KEY=%USERPROFILE%\.ssh\vpn_server
set LOCAL_BACKUP_DIR=%USERPROFILE%\vpn-backups

if "%BACKUP_PASSPHRASE%"=="" (
    echo ERROR: BACKUP_PASSPHRASE not set in environment.
    echo Run: set BACKUP_PASSPHRASE=^<your passphrase^>
    exit /b 1
)

if not exist "%LOCAL_BACKUP_DIR%" mkdir "%LOCAL_BACKUP_DIR%"

echo Finding latest backup on server...
for /f "delims=" %%i in ('ssh vpn-server "sudo ls -1t /var/backups/vpn/vpn-state-*.tar.gz | head -1"') do set REMOTE_PATH=%%i

if "%REMOTE_PATH%"=="" (
    echo ERROR: No backup found on server. Run backup.sh first.
    exit /b 1
)

for %%i in ("%REMOTE_PATH%") do set FILENAME=%%~ni
set LOCAL_ARCHIVE=%LOCAL_BACKUP_DIR%\%FILENAME%.tar.gz
set ENCRYPTED=%LOCAL_BACKUP_DIR%\%FILENAME%.tar.gz.gpg

echo Pulling %REMOTE_PATH% ...
scp -i "%SSH_KEY%" %SERVER%:"%REMOTE_PATH%" "%LOCAL_ARCHIVE%"

if not exist "%LOCAL_ARCHIVE%" (
    echo ERROR: scp failed.
    exit /b 1
)

echo Encrypting locally...
echo %BACKUP_PASSPHRASE%| gpg --batch --yes --passphrase-fd 0 ^
    --symmetric --cipher-algo AES256 ^
    --output "%ENCRYPTED%" "%LOCAL_ARCHIVE%"

if not exist "%ENCRYPTED%" (
    echo ERROR: encryption failed.
    exit /b 1
)

del /q "%LOCAL_ARCHIVE%"

echo Done. Backup: %ENCRYPTED%
endlocal
