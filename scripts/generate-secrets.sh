#!/bin/bash

set -e

echo "Generating secure secrets..."
echo ""

SECRET_KEY=$(openssl rand -base64 64 | tr -d '\n')
echo "SECRET_KEY=$SECRET_KEY"
echo ""

POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
echo ""

REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
echo "REDIS_PASSWORD=$REDIS_PASSWORD"
echo ""

echo "---"
echo "Copy these to your .env file"
echo "NEVER commit these values"
