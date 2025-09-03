@echo off
REM Russian Trading Bot Production Deployment Script for Windows
REM Automated deployment with Russian market configuration

setlocal enabledelayedexpansion

REM Configuration
set ENVIRONMENT=production
set COMPOSE_FILE=infrastructure\docker-compose.prod.yml
set ENV_FILE=.env.production

echo 🚀 Starting deployment of Russian Trading Bot to %ENVIRONMENT% environment

REM Check prerequisites
echo 📋 Checking prerequisites...

REM Check if Docker is installed and running
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not installed
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker daemon is not running
    exit /b 1
)

REM Check if Docker Compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose is not installed
    exit /b 1
)

REM Check if environment file exists
if not exist "%ENV_FILE%" (
    echo ❌ Environment file not found: %ENV_FILE%
    echo Please create the environment file with required variables
    exit /b 1
)

echo ✅ Prerequisites check passed

REM Create necessary directories
echo 📁 Creating directory structure...
if not exist "logs" mkdir logs
if not exist "logs\trading_bot" mkdir logs\trading_bot
if not exist "logs\moex_api" mkdir logs\moex_api
if not exist "logs\news_analysis" mkdir logs\news_analysis
if not exist "logs\risk_management" mkdir logs\risk_management
if not exist "logs\trade_execution" mkdir logs\trade_execution
if not exist "logs\nginx" mkdir logs\nginx
if not exist "config\production" mkdir config\production
if not exist "config\secrets" mkdir config\secrets
if not exist "data\models" mkdir data\models
if not exist "data\cache" mkdir data\cache
if not exist "backups" mkdir backups

echo ✅ Directory structure created

REM Set up Russian locale configuration
echo 🇷🇺 Setting up Russian locale configuration...
(
echo LANG=ru_RU.UTF-8
echo LANGUAGE=ru_RU:ru
echo LC_ALL=ru_RU.UTF-8
echo LC_TIME=ru_RU.UTF-8
echo LC_MONETARY=ru_RU.UTF-8
echo LC_NUMERIC=ru_RU.UTF-8
echo TZ=Europe/Moscow
) > config\production\locale.conf

REM Generate SSL certificates (self-signed for development)
echo 🔐 Setting up SSL certificates...
if not exist "infrastructure\nginx\ssl" mkdir infrastructure\nginx\ssl
if not exist "infrastructure\nginx\ssl\cert.pem" (
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout infrastructure\nginx\ssl\key.pem -out infrastructure\nginx\ssl\cert.pem -subj "/C=RU/ST=Moscow/L=Moscow/O=Russian Trading Bot/CN=localhost"
    echo ✅ Self-signed SSL certificates generated
)

REM Build and deploy services
echo 🏗️ Building and deploying services...

REM Pull latest images
docker-compose -f %COMPOSE_FILE% pull

REM Build custom images
docker-compose -f %COMPOSE_FILE% build --no-cache

REM Start services in correct order
echo 🚀 Starting services...

REM Start infrastructure services first
docker-compose -f %COMPOSE_FILE% up -d postgres redis elasticsearch

REM Wait for database to be ready
echo ⏳ Waiting for database to be ready...
timeout /t 60 /nobreak >nul
docker-compose -f %COMPOSE_FILE% exec -T postgres pg_isready -U trading_user -d russian_trading
if errorlevel 1 (
    echo ❌ Database failed to start within timeout
    exit /b 1
)

REM Start remaining services
docker-compose -f %COMPOSE_FILE% up -d

REM Wait for services to be healthy
echo 🏥 Checking service health...
timeout /t 30 /nobreak >nul

REM Verify deployment
echo 🔍 Verifying deployment...

REM Check API endpoints
curl -f http://localhost/health >nul 2>&1
if errorlevel 1 (
    echo ⚠️ http://localhost/health - Not responding
) else (
    echo ✅ http://localhost/health - OK
)

curl -f http://localhost/api/status >nul 2>&1
if errorlevel 1 (
    echo ⚠️ http://localhost/api/status - Not responding
) else (
    echo ✅ http://localhost/api/status - OK
)

REM Display deployment summary
echo.
echo 🎉 Deployment completed successfully!
echo.
echo 📋 Service URLs:
echo    Trading Bot API: http://localhost/api
echo    Web Dashboard:   http://localhost
echo    Prometheus:      http://localhost:9090
echo    Grafana:         http://localhost:3000
echo    Kibana:          http://localhost:5601
echo.
echo 📁 Important Directories:
echo    Logs:    .\logs\
echo    Config:  .\config\
echo    Backups: .\backups\
echo.
echo 🇷🇺 Russian Market Configuration:
echo    Timezone: Europe/Moscow
echo    Locale:   ru_RU.UTF-8
echo    Currency: RUB
echo    Market:   MOEX
echo.
echo 📚 Next Steps:
echo    1. Configure MOEX API credentials in the web dashboard
echo    2. Set up Russian broker API connections
echo    3. Configure news feed subscriptions
echo    4. Review and adjust risk management parameters
echo    5. Start paper trading to validate the system
echo.
echo 🔧 Management Commands:
echo    View logs:    docker-compose -f %COMPOSE_FILE% logs -f
echo    Stop system:  docker-compose -f %COMPOSE_FILE% down
echo    Restart:      docker-compose -f %COMPOSE_FILE% restart
echo    Backup:       .\infrastructure\backup\backup_script.bat
echo.

REM Send deployment notification
curl -X POST "http://localhost/api/notifications/deployment" -H "Content-Type: application/json" -d "{\"status\": \"success\", \"environment\": \"%ENVIRONMENT%\", \"timestamp\": \"%date% %time%\", \"message\": \"Развертывание системы торговли завершено успешно\"}" 2>nul

echo ✅ Russian Trading Bot deployment completed successfully!

endlocal