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
    cp ../config/.env.docker .env
    echo "✅ .env file created"
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

# Check service health
echo ""
echo "🔍 Checking service health..."

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready -U authuser > /dev/null 2>&1; then
    echo "✅ PostgreSQL: healthy"
else
    echo "❌ PostgreSQL: unhealthy"
fi

# Check Redis
if docker-compose exec -T redis redis-cli -a redispass ping > /dev/null 2>&1; then
    echo "✅ Redis: healthy"
else
    echo "❌ Redis: unhealthy"
fi

# Check Backend
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend: healthy"
else
    echo "⏳ Backend: starting..."
    sleep 10
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend: healthy"
    else
        echo "❌ Backend: unhealthy"
    fi
fi

# Check Frontend
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend: healthy"
else
    echo "⏳ Frontend: starting..."
fi

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
