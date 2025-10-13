#!/bin/bash

# Docker Development Environment Startup Script

set -e

echo "🚀 Starting Hybrid Auth System (Docker)"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Copy environment file if not exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    if cp ../config/.env.docker .env; then
        echo "✅ .env file created"
    else
        echo "❌ Failed to create .env file from template. Please check if ../config/.env.docker exists and try again."
        exit 1
    fi
else
    echo "✅ .env file exists"
fi

# Build and start services
echo ""
echo "🔨 Building and starting services..."
docker-compose up -d --build

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

# Function to check service health
check_service() {
    local name="$1"
    local cmd="$2"
    local healthy_msg="$3"
    local unhealthy_msg="$4"
    local retry="${5:-0}"
    local wait="${6:-0}"

    if eval "$cmd" > /dev/null 2>&1; then
        echo "✅ $healthy_msg"
    else
        if [ "$retry" -gt 0 ]; then
            echo "⏳ $name: retrying in $wait seconds..."
            sleep "$wait"
            if eval "$cmd" > /dev/null 2>&1; then
                echo "✅ $healthy_msg"
                return
            fi
        fi
        echo "❌ $unhealthy_msg"
        exit 1
    fi
}

echo ""
echo "🔍 Checking service health..."

# Check PostgreSQL
check_service "PostgreSQL" \
    "docker-compose exec -T postgres pg_isready -U authuser" \
    "PostgreSQL: healthy" \
    "PostgreSQL: unhealthy"

# Check Redis
check_service "Redis" \
    "docker-compose exec -T redis redis-cli -a redispass ping | grep -q PONG" \
    "Redis: healthy" \
    "Redis: unhealthy"

# Check Backend (with retry)
check_service "Backend" \
    "curl -f http://localhost:8000/health" \
    "Backend: healthy" \
    "Backend: unhealthy" \
    1 10

# Check Frontend (with retry)
check_service "Frontend" \
    "curl -f http://localhost:3000" \
    "Frontend: healthy" \
    "Frontend: unhealthy" \
    1 10

echo ""
echo "🎉 Services are running!"
echo ""
echo "📍 Access URLs:"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "📊 View logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose down"
