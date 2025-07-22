#!/bin/bash

# PMA - Prescription Management App
# Enhanced Deployment Script with Automation Support
# Supports both manual and CI/CD automated deployments

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
print_message() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

print_message $BLUE "🏥 PMA - Prescription Management App Deployment"
print_message $PURPLE "Enhanced Automated Deployment System"
print_message $BLUE "============================================="

# Detect deployment environment
if [ "${CI}" = "true" ]; then
    print_message $YELLOW "🤖 CI/CD Automated Deployment Detected"
    DEPLOY_ENV="ci"
elif [ -n "${PRODUCTION}" ]; then
    DEPLOY_ENV="production"
else
    DEPLOY_ENV="development"
fi

# Get deployment type from argument or environment
DEPLOY_TYPE=${1:-$DEPLOY_ENV}

print_message $YELLOW "📋 Deployment Configuration:"
print_message $YELLOW "   Environment: $DEPLOY_TYPE"
print_message $YELLOW "   Date: $(date)"
print_message $YELLOW "   Version: ${GITHUB_SHA:-$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')}"

# Check if required commands exist
check_dependency() {
    if ! command -v $1 >/dev/null 2>&1; then
        print_message $RED "❌ $1 is required but not installed."
        if [ "${CI}" = "true" ]; then
            print_message $RED "This is a CI environment - dependency should be pre-installed"
            exit 1
        else
            print_message $YELLOW "Please install $1 and run again."
            exit 1
        fi
    else
        print_message $GREEN "✅ $1 is available"
    fi
}

print_message $BLUE "🔍 Checking dependencies..."
check_dependency "docker"
if [ "$DEPLOY_TYPE" != "ci" ]; then
    check_dependency "docker-compose"
fi

# Create necessary directories
print_message $BLUE "📁 Creating directories..."
mkdir -p logs deployment-artifacts

# Environment-specific configuration
case $DEPLOY_TYPE in
    "production")
        print_message $GREEN "🚀 Production Deployment Configuration"
        BACKEND_URL="https://api.pma.healthcare"
        DB_NAME="pma_production"
        ;;
    "staging")
        print_message $YELLOW "🧪 Staging Deployment Configuration"
        BACKEND_URL="https://staging-api.pma.healthcare"
        DB_NAME="pma_staging"
        ;;
    "ci")
        print_message $BLUE "🤖 CI/CD Testing Configuration"
        BACKEND_URL="http://localhost:8001"
        DB_NAME="pma_ci_test"
        ;;
    *)
        print_message $GREEN "🔧 Development Deployment Configuration"
        BACKEND_URL="http://localhost:8001"
        DB_NAME="prescription_db"
        ;;
esac

# Generate environment files if they don't exist
generate_env_files() {
    if [ ! -f backend/.env ]; then
        print_message $YELLOW "⚙️  Creating backend environment file..."
        cat > backend/.env << EOF
MONGO_URL=mongodb://mongodb:27017/
DB_NAME=$DB_NAME
SECRET_KEY=$(openssl rand -base64 32 2>/dev/null || echo "fallback-secret-key-$(date +%s)")
ENVIRONMENT=$DEPLOY_TYPE
EOF
    fi

    if [ ! -f frontend/.env ]; then
        print_message $YELLOW "⚙️  Creating frontend environment file..."
        cat > frontend/.env << EOF
REACT_APP_BACKEND_URL=$BACKEND_URL
WDS_SOCKET_HOST=localhost
WDS_SOCKET_PORT=443
REACT_APP_ENV=$DEPLOY_TYPE
EOF
    fi
}

generate_env_files

# Build Docker image
build_docker_image() {
    print_message $BLUE "🏗️  Building Docker image..."
    
    # Build with version tag
    VERSION_TAG=${GITHUB_SHA:-$(date +%Y%m%d-%H%M%S)}
    docker build -t pma-app:$VERSION_TAG -t pma-app:latest .
    
    print_message $GREEN "✅ Docker image built: pma-app:$VERSION_TAG"
}

# Deployment strategy based on type
deploy_application() {
    case $DEPLOY_TYPE in
        "production"|"staging")
            print_message $GREEN "🚀 Starting $DEPLOY_TYPE deployment..."
            if [ -f docker-compose.prod.yml ]; then
                docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
            else
                docker-compose up -d --build
            fi
            ;;
        "ci")
            print_message $BLUE "🤖 CI deployment - building for testing..."
            build_docker_image
            ;;
        *)
            print_message $GREEN "🔧 Starting development deployment..."
            docker-compose up -d --build
            ;;
    esac
}

# Health check with retry logic
health_check() {
    print_message $BLUE "🔍 Running health checks..."
    
    local max_attempts=10
    local attempt=1
    
    # Function to check endpoint with retries
    check_endpoint() {
        local url=$1
        local service_name=$2
        
        while [ $attempt -le $max_attempts ]; do
            if curl -f $url >/dev/null 2>&1; then
                print_message $GREEN "✅ $service_name is healthy"
                return 0
            else
                print_message $YELLOW "⏳ Waiting for $service_name... (attempt $attempt/$max_attempts)"
                sleep 5
                ((attempt++))
            fi
        done
        
        print_message $RED "❌ $service_name health check failed after $max_attempts attempts"
        return 1
    }
    
    # Skip health checks in CI mode
    if [ "$DEPLOY_TYPE" = "ci" ]; then
        print_message $BLUE "⏭️  Skipping health checks in CI mode"
        return 0
    fi
    
    # Backend health check
    if ! check_endpoint "http://localhost:8001/api/health" "Backend"; then
        print_message $RED "Backend logs:"
        docker-compose logs backend
        exit 1
    fi
    
    # MongoDB health check
    if ! docker exec $(docker-compose ps -q mongodb 2>/dev/null) mongosh --eval "db.runCommand('ping')" >/dev/null 2>&1; then
        print_message $RED "❌ MongoDB health check failed"
        docker-compose logs mongodb
        exit 1
    else
        print_message $GREEN "✅ MongoDB is healthy"
    fi
}

# Generate deployment report
generate_deployment_report() {
    print_message $BLUE "📊 Generating deployment report..."
    
    cat > deployment-artifacts/deployment-report.json << EOF
{
  "deployment": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "type": "$DEPLOY_TYPE",
    "version": "${GITHUB_SHA:-$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')}",
    "user": "$(whoami)",
    "status": "successful"
  },
  "services": {
    "backend": {
      "url": "$BACKEND_URL/api",
      "health_endpoint": "$BACKEND_URL/api/health",
      "documentation": "$BACKEND_URL/api/docs"
    },
    "database": {
      "name": "$DB_NAME",
      "type": "MongoDB"
    }
  },
  "urls": {
    "application": "https://ab6009e8-2e3e-4cd0-b3b8-a452a86b19f9.preview.emergentagent.com",
    "api_docs": "$BACKEND_URL/api/docs",
    "repository": "https://github.com/Dev1-Hebroux/PMA"
  }
}
EOF

    print_message $GREEN "✅ Deployment report generated"
}

# Main deployment flow
main() {
    print_message $BLUE "🚀 Starting PMA deployment process..."
    
    deploy_application
    
    if [ "$DEPLOY_TYPE" != "ci" ]; then
        print_message $BLUE "⏳ Waiting for services to initialize..."
        sleep 10
        health_check
    fi
    
    generate_deployment_report
    
    print_message $GREEN "🎉 Deployment completed successfully!"
    print_message $GREEN "🌐 Application Information:"
    print_message $GREEN "   Environment: $DEPLOY_TYPE"
    print_message $GREEN "   Frontend: https://ab6009e8-2e3e-4cd0-b3b8-a452a86b19f9.preview.emergentagent.com"
    print_message $GREEN "   Backend API: $BACKEND_URL/api"
    print_message $GREEN "   API Documentation: $BACKEND_URL/api/docs"
    
    if [ "$DEPLOY_TYPE" != "ci" ]; then
        print_message $BLUE "📊 Container Status:"
        docker-compose ps
        
        print_message $BLUE "📝 Useful commands:"
        print_message $BLUE "   View logs: docker-compose logs -f"
        print_message $BLUE "   Stop services: docker-compose down"
        print_message $BLUE "   Restart: docker-compose restart"
    fi
    
    print_message $GREEN "✨ PMA is now running and ready for healthcare operations!"
    print_message $BLUE "🏥 Built with ❤️  for better healthcare management"
}

# Run main deployment
main "$@"