#!/bin/bash

# PMA - Prescription Management App
# Deployment Script
# Powered by Innovating Chaos

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_message() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

print_message $BLUE "🏥 PMA - Prescription Management App Deployment"
print_message $BLUE "Powered by Innovating Chaos"
print_message $BLUE "=================================="

# Check if required commands exist
command -v git >/dev/null 2>&1 || { print_message $RED "❌ Git is required but not installed. Aborting."; exit 1; }
command -v docker >/dev/null 2>&1 || { print_message $RED "❌ Docker is required but not installed. Aborting."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { print_message $RED "❌ Docker Compose is required but not installed. Aborting."; exit 1; }

# Get deployment type
DEPLOY_TYPE=${1:-development}

print_message $YELLOW "📋 Deployment Configuration:"
print_message $YELLOW "   Type: $DEPLOY_TYPE"
print_message $YELLOW "   Date: $(date)"
print_message $YELLOW "   User: $(whoami)"

# Create necessary directories
print_message $BLUE "📁 Creating directories..."
mkdir -p logs docker

# Generate environment files if they don't exist
if [ ! -f backend/.env ]; then
    print_message $YELLOW "⚙️  Creating backend environment file..."
    cat > backend/.env << EOF
MONGO_URL=mongodb://mongodb:27017/
DB_NAME=prescription_db
SECRET_KEY=$(openssl rand -base64 32)
EOF
fi

if [ ! -f frontend/.env ]; then
    print_message $YELLOW "⚙️  Creating frontend environment file..."
    cat > frontend/.env << EOF
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_HOST=localhost
WDS_SOCKET_PORT=443
EOF
fi

# Build and start services
print_message $BLUE "🏗️  Building and starting services..."

if [ "$DEPLOY_TYPE" = "production" ]; then
    print_message $GREEN "🚀 Production deployment"
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
else
    print_message $GREEN "🔧 Development deployment"
    docker-compose up -d --build
fi

# Wait for services to be ready
print_message $BLUE "⏳ Waiting for services to start..."
sleep 10

# Health check
print_message $BLUE "🔍 Running health checks..."

# Check backend
if curl -f http://localhost:8001/api/health >/dev/null 2>&1; then
    print_message $GREEN "✅ Backend is healthy"
else
    print_message $RED "❌ Backend health check failed"
    exit 1
fi

# Check frontend (only in production mode)
if [ "$DEPLOY_TYPE" = "production" ]; then
    if curl -f http://localhost >/dev/null 2>&1; then
        print_message $GREEN "✅ Frontend is healthy"
    else
        print_message $RED "❌ Frontend health check failed"
        exit 1
    fi
fi

# Check MongoDB
if docker exec $(docker-compose ps -q mongodb) mongosh --eval "db.runCommand('ping')" >/dev/null 2>&1; then
    print_message $GREEN "✅ MongoDB is healthy"
else
    print_message $RED "❌ MongoDB health check failed"
    exit 1
fi

print_message $GREEN "🎉 Deployment completed successfully!"
print_message $GREEN "🌐 Application URLs:"
print_message $GREEN "   Frontend: http://localhost"
print_message $GREEN "   Backend API: http://localhost:8001"
print_message $GREEN "   API Documentation: http://localhost:8001/docs"
print_message $GREEN "   MongoDB: localhost:27017"

print_message $BLUE "📊 Container Status:"
docker-compose ps

print_message $BLUE "📝 View logs with:"
print_message $BLUE "   docker-compose logs -f"

print_message $BLUE "🛑 Stop services with:"
print_message $BLUE "   docker-compose down"

print_message $GREEN "✨ PMA is now running and ready for use!"
print_message $BLUE "Built with ❤️  by Innovating Chaos"