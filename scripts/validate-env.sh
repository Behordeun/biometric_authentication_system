#!/bin/bash

# Environment validation script
# Ensures proper .env symlink configuration

set -e

echo "🔍 Validating environment configuration..."

# Check if backend/.env exists
if [ ! -f backend/.env ]; then
    echo "❌ Backend .env file missing at backend/.env"
    echo "   Run: cp backend/.env.example backend/.env"
    exit 1
fi

# Check if docker/.env is a symlink
if [ ! -L docker/.env ]; then
    if [ -f docker/.env ]; then
        echo "⚠️  Regular .env file found in docker/, removing..."
        rm docker/.env
    fi
    echo "🔗 Creating .env symlink..."
    ln -sf ../backend/.env docker/.env
fi

# Validate symlink target
if [ ! -f docker/.env ]; then
    echo "❌ Symlink target is invalid"
    exit 1
fi

# Check if symlink points to correct file
LINK_TARGET=$(readlink docker/.env)
if [ "$LINK_TARGET" != "../backend/.env" ]; then
    echo "❌ Symlink points to wrong target: $LINK_TARGET"
    echo "   Expected: ../backend/.env"
    exit 1
fi

echo "✅ Environment configuration is valid"
echo "   Backend .env: $(ls -la backend/.env | awk '{print $5, $6, $7, $8, $9}')"
echo "   Docker symlink: $(ls -la docker/.env | awk '{print $9, $10, $11}')"
