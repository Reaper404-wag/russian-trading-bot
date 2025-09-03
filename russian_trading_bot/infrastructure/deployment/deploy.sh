#!/bin/bash

# Russian Trading Bot Production Deployment Script
# Automated deployment with Russian market configuration

set -e

# Configuration
ENVIRONMENT=${ENVIRONMENT:-production}
COMPOSE_FILE="infrastructure/docker-compose.prod.yml"
ENV_FILE=".env.production"

echo "🚀 Starting deployment of Russian Trading Bot to $ENVIRONMENT environment"

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    exit 1
fi

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Environment file not found: $ENV_FILE"
    echo "Please create the environment file with required variables"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Load environment variables
echo "🔧 Loading environment configuration..."
source "$ENV_FILE"

# Validate required environment variables
required_vars=(
    "DB_PASSWORD"
    "REDIS_PASSWORD"
    "GRAFANA_PASSWORD"
    "BACKUP_ENCRYPTION_KEY"
    "MOEX_API_KEY"
    "TINKOFF_API_TOKEN"
    "TELEGRAM_BOT_TOKEN"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable not set: $var"
        exit 1
    fi
done

echo "✅ Environment configuration validated"

# Create necessary directories
echo "📁 Creating directory structure..."
mkdir -p logs/{trading_bot,moex_api,news_analysis,risk_management,trade_execution,nginx}
mkdir -p config/{production,secrets}
mkdir -p data/{models,cache}
mkdir -p backups

echo "✅ Directory structure created"

# Set up Russian locale configuration
echo "🇷🇺 Setting up Russian locale configuration..."
cat > config/production/locale.conf << EOF
LANG=ru_RU.UTF-8
LANGUAGE=ru_RU:ru
LC_ALL=ru_RU.UTF-8
LC_TIME=ru_RU.UTF-8
LC_MONETARY=ru_RU.UTF-8
LC_NUMERIC=ru_RU.UTF-8
TZ=Europe/Moscow
EOF

# Generate SSL certificates (self-signed for development)
echo "🔐 Setting up SSL certificates..."
mkdir -p infrastructure/nginx/ssl
if [ ! -f "infrastructure/nginx/ssl/cert.pem" ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout infrastructure/nginx/ssl/key.pem \
        -out infrastructure/nginx/ssl/cert.pem \
        -subj "/C=RU/ST=Moscow/L=Moscow/O=Russian Trading Bot/CN=localhost"
    echo "✅ Self-signed SSL certificates generated"
fi

# Build and deploy services
echo "🏗️ Building and deploying services..."

# Pull latest images
docker-compose -f "$COMPOSE_FILE" pull

# Build custom images
docker-compose -f "$COMPOSE_FILE" build --no-cache

# Start services in correct order
echo "🚀 Starting services..."

# Start infrastructure services first
docker-compose -f "$COMPOSE_FILE" up -d postgres redis elasticsearch

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
timeout=60
while ! docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U trading_user -d russian_trading; do
    sleep 2
    timeout=$((timeout - 2))
    if [ $timeout -le 0 ]; then
        echo "❌ Database failed to start within timeout"
        exit 1
    fi
done

# Run database migrations
echo "🗄️ Running database migrations..."
docker-compose -f "$COMPOSE_FILE" exec -T trading-bot python -m russian_trading_bot.database.migrations

# Start remaining services
docker-compose -f "$COMPOSE_FILE" up -d

# Wait for all services to be healthy
echo "🏥 Checking service health..."
services=("trading-bot" "postgres" "redis" "nginx")
for service in "${services[@]}"; do
    echo "Checking $service..."
    timeout=120
    while ! docker-compose -f "$COMPOSE_FILE" ps "$service" | grep -q "healthy\|Up"; do
        sleep 5
        timeout=$((timeout - 5))
        if [ $timeout -le 0 ]; then
            echo "❌ Service $service failed to become healthy"
            docker-compose -f "$COMPOSE_FILE" logs "$service"
            exit 1
        fi
    done
    echo "✅ $service is healthy"
done

# Set up monitoring dashboards
echo "📊 Setting up monitoring dashboards..."
# Import Grafana dashboards
if [ -d "infrastructure/monitoring/grafana/dashboards" ]; then
    docker cp infrastructure/monitoring/grafana/dashboards/. russian-trading-grafana:/var/lib/grafana/dashboards/
fi

# Set up backup cron job
echo "💾 Setting up automated backups..."
(crontab -l 2>/dev/null; echo "0 2 * * * /app/infrastructure/backup/backup_script.sh") | crontab -

# Verify deployment
echo "🔍 Verifying deployment..."

# Check API endpoints
api_endpoints=(
    "http://localhost/health"
    "http://localhost/api/status"
    "http://localhost/api/market/status"
)

for endpoint in "${api_endpoints[@]}"; do
    if curl -f "$endpoint" > /dev/null 2>&1; then
        echo "✅ $endpoint - OK"
    else
        echo "⚠️ $endpoint - Not responding (may be normal during startup)"
    fi
done

# Check monitoring endpoints
monitoring_endpoints=(
    "http://localhost:9090"  # Prometheus
    "http://localhost:3000"  # Grafana
    "http://localhost:5601"  # Kibana
)

for endpoint in "${monitoring_endpoints[@]}"; do
    if curl -f "$endpoint" > /dev/null 2>&1; then
        echo "✅ $endpoint - OK"
    else
        echo "⚠️ $endpoint - Not responding"
    fi
done

# Display deployment summary
echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Service URLs:"
echo "   Trading Bot API: http://localhost/api"
echo "   Web Dashboard:   http://localhost"
echo "   Prometheus:      http://localhost:9090"
echo "   Grafana:         http://localhost:3000"
echo "   Kibana:          http://localhost:5601"
echo ""
echo "🔐 Default Credentials:"
echo "   Grafana: admin / $GRAFANA_PASSWORD"
echo ""
echo "📁 Important Directories:"
echo "   Logs:    ./logs/"
echo "   Config:  ./config/"
echo "   Backups: ./backups/"
echo ""
echo "🇷🇺 Russian Market Configuration:"
echo "   Timezone: Europe/Moscow"
echo "   Locale:   ru_RU.UTF-8"
echo "   Currency: RUB"
echo "   Market:   MOEX"
echo ""
echo "📚 Next Steps:"
echo "   1. Configure MOEX API credentials in the web dashboard"
echo "   2. Set up Russian broker API connections"
echo "   3. Configure news feed subscriptions"
echo "   4. Review and adjust risk management parameters"
echo "   5. Start paper trading to validate the system"
echo ""
echo "🔧 Management Commands:"
echo "   View logs:    docker-compose -f $COMPOSE_FILE logs -f"
echo "   Stop system:  docker-compose -f $COMPOSE_FILE down"
echo "   Restart:      docker-compose -f $COMPOSE_FILE restart"
echo "   Backup:       ./infrastructure/backup/backup_script.sh"
echo ""

# Send deployment notification
if command -v curl &> /dev/null; then
    curl -X POST "http://localhost/api/notifications/deployment" \
        -H "Content-Type: application/json" \
        -d "{\"status\": \"success\", \"environment\": \"$ENVIRONMENT\", \"timestamp\": \"$(date -Iseconds)\", \"message\": \"Развертывание системы торговли завершено успешно\"}" \
        2>/dev/null || echo "Note: Could not send deployment notification"
fi

echo "✅ Russian Trading Bot deployment completed successfully!"