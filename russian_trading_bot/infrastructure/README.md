# Russian Trading Bot - Production Infrastructure

This directory contains all the necessary infrastructure components for deploying the Russian Trading Bot in a production environment with Russian data residency compliance.

## 🏗️ Architecture Overview

The production infrastructure consists of:

- **Application Layer**: Russian Trading Bot (Python/FastAPI)
- **Database Layer**: PostgreSQL with Russian locale support
- **Cache Layer**: Redis for session management and caching
- **Web Layer**: Nginx reverse proxy with SSL termination
- **Monitoring Stack**: Prometheus, Grafana, ELK Stack
- **Backup System**: Automated encrypted backups with Russian compliance

## 📁 Directory Structure

```
infrastructure/
├── docker-compose.prod.yml     # Production Docker Compose configuration
├── Dockerfile.prod            # Production Docker image
├── .env.production.template   # Environment variables template
├── nginx/
│   └── nginx.conf            # Nginx configuration with Russian market optimizations
├── monitoring/
│   ├── prometheus.yml        # Prometheus configuration
│   ├── logstash.conf        # Logstash configuration for Russian logs
│   └── health_monitor.py    # Comprehensive health monitoring
├── backup/
│   ├── backup_script.sh     # Linux backup script
│   ├── backup_script.bat    # Windows backup script
│   └── restore_script.sh    # Restore script
└── deployment/
    ├── deploy.sh            # Linux deployment script
    └── deploy.bat           # Windows deployment script
```

## 🚀 Quick Start

### Prerequisites

1. **Docker & Docker Compose**: Ensure Docker and Docker Compose are installed
2. **Environment Configuration**: Copy and configure environment variables
3. **SSL Certificates**: Generate or provide SSL certificates
4. **Russian Locale**: System should support Russian locale (ru_RU.UTF-8)

### Deployment Steps

1. **Configure Environment**:
   ```bash
   cp .env.production.template .env.production
   # Edit .env.production with your actual values
   ```

2. **Deploy on Linux**:
   ```bash
   chmod +x deployment/deploy.sh
   ./deployment/deploy.sh
   ```

3. **Deploy on Windows**:
   ```cmd
   deployment\deploy.bat
   ```

## 🔧 Configuration

### Environment Variables

Key environment variables that must be configured:

#### Database Configuration
- `DB_PASSWORD`: Secure PostgreSQL password
- `DB_HOST`: Database host (default: postgres)
- `DB_NAME`: Database name (default: russian_trading)

#### Security Configuration
- `BACKUP_ENCRYPTION_KEY`: 32-character encryption key for backups
- `JWT_SECRET_KEY`: JWT token signing key
- `API_SECRET_KEY`: API authentication key

#### Russian Market APIs
- `MOEX_API_KEY`: MOEX (Moscow Exchange) API key
- `TINKOFF_API_TOKEN`: Tinkoff Invest API token
- `FINAM_API_KEY`: Finam broker API key

#### News Sources
- `RBC_RSS_URL`: RBC news RSS feed
- `VEDOMOSTI_RSS_URL`: Vedomosti news RSS feed
- `KOMMERSANT_RSS_URL`: Kommersant news RSS feed
- `INTERFAX_API_KEY`: Interfax news API key

#### Notifications
- `TELEGRAM_BOT_TOKEN`: Telegram bot token for alerts
- `EMAIL_USERNAME`: Email for notifications
- `EMAIL_PASSWORD`: Email password

### Russian Market Specific Configuration

- **Timezone**: Europe/Moscow
- **Locale**: ru_RU.UTF-8
- **Currency**: RUB
- **Trading Hours**: 10:00-18:45 MSK
- **Market**: MOEX (Moscow Exchange)

## 📊 Monitoring

### Health Monitoring

The system includes comprehensive health monitoring:

- **Database Health**: PostgreSQL connectivity and data freshness
- **Cache Health**: Redis performance and connectivity
- **API Health**: MOEX API and news sources availability
- **System Resources**: CPU, memory, and disk usage
- **Application Health**: Trading bot service status

### Monitoring Endpoints

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/[GRAFANA_PASSWORD])
- **Kibana**: http://localhost:5601
- **Health API**: http://localhost/health

### Alerts

Automated alerts are sent via:
- Telegram notifications
- Email notifications
- System logs

## 💾 Backup & Recovery

### Automated Backups

Backups run daily at 2:00 AM Moscow time and include:

- PostgreSQL database dump
- Redis data snapshot
- Application logs
- Configuration files
- ML models (Russian sentiment analysis, etc.)

### Backup Features

- **Encryption**: AES-256 encryption for all backup files
- **Retention**: 30-day retention policy
- **Compliance**: Russian data residency requirements
- **Verification**: Automatic backup integrity checks

### Manual Backup

**Linux**:
```bash
./infrastructure/backup/backup_script.sh
```

**Windows**:
```cmd
infrastructure\backup\backup_script.bat
```

### Restore Process

```bash
./infrastructure/backup/restore_script.sh <backup_timestamp>
```

## 🔒 Security

### Data Protection

- **Encryption**: All sensitive data encrypted at rest
- **SSL/TLS**: HTTPS encryption for all web traffic
- **Access Control**: Role-based access control
- **Audit Logs**: Comprehensive audit trail

### Russian Compliance

- **Data Residency**: All data stored within Russian jurisdiction
- **Personal Data**: GDPR/Russian data protection compliance
- **Financial Regulations**: Central Bank of Russia compliance
- **Audit Requirements**: 5-year audit log retention

## 🌐 Network Configuration

### Port Mapping

- **80**: HTTP (redirects to HTTPS)
- **443**: HTTPS (main application)
- **3000**: Grafana dashboard
- **5601**: Kibana logs
- **9090**: Prometheus metrics

### Internal Network

All services communicate through a private Docker network (`trading-network`) for security.

## 🔧 Maintenance

### Regular Maintenance Tasks

1. **Daily**: Automated backups and health checks
2. **Weekly**: Log rotation and cleanup
3. **Monthly**: Security updates and dependency updates
4. **Quarterly**: Performance optimization and capacity planning

### Troubleshooting

#### Common Issues

1. **Database Connection Issues**:
   ```bash
   docker-compose logs postgres
   docker-compose restart postgres
   ```

2. **MOEX API Connectivity**:
   ```bash
   curl -I https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json
   ```

3. **Memory Issues**:
   ```bash
   docker stats
   # Check system resources in Grafana
   ```

#### Log Locations

- Application logs: `./logs/trading_bot/`
- MOEX API logs: `./logs/moex_api/`
- News analysis logs: `./logs/news_analysis/`
- Risk management logs: `./logs/risk_management/`
- Trade execution logs: `./logs/trade_execution/`
- Nginx logs: `./logs/nginx/`

## 📈 Performance Tuning

### Database Optimization

- Connection pooling: 20 connections
- Query optimization for Russian market data
- Indexing on frequently queried columns

### Cache Optimization

- Redis memory optimization
- Cache warming for frequently accessed data
- TTL optimization for market data

### Application Optimization

- Worker processes: 4 (configurable)
- Async processing for I/O operations
- Memory-efficient data structures

## 🆘 Support

### Emergency Contacts

In case of critical issues:

1. Check system health: http://localhost/health
2. Review logs in Kibana: http://localhost:5601
3. Check metrics in Grafana: http://localhost:3000
4. Review backup status: `./infrastructure/backup/backup_script.sh`

### Documentation

- [MOEX API Documentation](https://iss.moex.com/iss/reference/)
- [Tinkoff Invest API](https://tinkoff.github.io/investAPI/)
- [Russian Financial Regulations](https://cbr.ru/)

## 📝 Changelog

### Version 1.0.0
- Initial production infrastructure setup
- Russian market compliance implementation
- Comprehensive monitoring and alerting
- Automated backup and recovery system
- SSL/TLS security implementation

---

**Note**: This infrastructure is specifically designed for the Russian stock market (MOEX) and complies with Russian data residency and financial regulations. Ensure all API keys and credentials are properly secured before deployment.