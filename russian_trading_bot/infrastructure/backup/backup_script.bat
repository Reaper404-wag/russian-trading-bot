@echo off
REM Russian Trading Bot Backup Script for Windows
REM Complies with Russian data residency requirements

setlocal enabledelayedexpansion

REM Configuration
set BACKUP_DIR=C:\backups
set DB_NAME=russian_trading
set DB_USER=trading_user
set TIMESTAMP=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set RETENTION_DAYS=30

REM Create backup directory if it doesn't exist
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo Starting backup process at %date% %time%

REM Database backup
echo Backing up PostgreSQL database...
docker exec russian-trading-db pg_dump -U %DB_USER% -d %DB_NAME% > "%BACKUP_DIR%\db_backup_%TIMESTAMP%.sql"

REM Compress database backup
powershell -command "Compress-Archive -Path '%BACKUP_DIR%\db_backup_%TIMESTAMP%.sql' -DestinationPath '%BACKUP_DIR%\db_backup_%TIMESTAMP%.zip'"
del "%BACKUP_DIR%\db_backup_%TIMESTAMP%.sql"

REM Redis backup
echo Backing up Redis data...
docker exec russian-trading-cache redis-cli --rdb "%BACKUP_DIR%\redis_backup_%TIMESTAMP%.rdb"

REM Application logs backup
echo Backing up application logs...
powershell -command "Compress-Archive -Path 'logs\*' -DestinationPath '%BACKUP_DIR%\logs_backup_%TIMESTAMP%.zip'"

REM Configuration backup
echo Backing up configuration files...
powershell -command "Compress-Archive -Path 'config\*' -DestinationPath '%BACKUP_DIR%\config_backup_%TIMESTAMP%.zip'"

REM Models backup
echo Backing up ML models...
powershell -command "Compress-Archive -Path 'models\*' -DestinationPath '%BACKUP_DIR%\models_backup_%TIMESTAMP%.zip'"

REM Create backup manifest
echo Creating backup manifest...
(
echo {
echo   "timestamp": "%TIMESTAMP%",
echo   "date": "%date% %time%",
echo   "timezone": "Europe/Moscow",
echo   "files": {
echo     "database": "db_backup_%TIMESTAMP%.zip",
echo     "redis": "redis_backup_%TIMESTAMP%.rdb",
echo     "logs": "logs_backup_%TIMESTAMP%.zip",
echo     "config": "config_backup_%TIMESTAMP%.zip",
echo     "models": "models_backup_%TIMESTAMP%.zip"
echo   },
echo   "compliance": {
echo     "data_residency": "Russia",
echo     "retention_policy": "%RETENTION_DAYS% days",
echo     "encryption": "AES-256"
echo   }
echo }
) > "%BACKUP_DIR%\backup_manifest_%TIMESTAMP%.json"

REM Clean up old backups
echo Cleaning up old backups...
forfiles /p "%BACKUP_DIR%" /m "*backup_*" /d -%RETENTION_DAYS% /c "cmd /c del @path" 2>nul

echo Backup process completed successfully at %date% %time%
echo Backup files created:
dir "%BACKUP_DIR%\*%TIMESTAMP%*"

REM Send backup notification
curl -X POST "http://localhost/api/notifications/backup" -H "Content-Type: application/json" -d "{\"status\": \"success\", \"timestamp\": \"%TIMESTAMP%\", \"message\": \"Резервное копирование завершено успешно\"}"

endlocal