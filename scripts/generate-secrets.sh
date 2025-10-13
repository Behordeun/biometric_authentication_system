#!/bin/bash

set -e

echo "Generating secure secrets..."
echo ""

SECRET_KEY=$(openssl rand -base64 64 | tr -d '\n')
if [ $? -ne 0 ] || [ -z "$SECRET_KEY" ]; then
	echo "❌ Failed to generate SECRET_KEY"
	exit 1
fi
echo "SECRET_KEY=$SECRET_KEY"
echo ""

POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
if [ $? -ne 0 ] || [ -z "$POSTGRES_PASSWORD" ]; then
	echo "❌ Failed to generate POSTGRES_PASSWORD"
	exit 1
fi
echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
echo ""

REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
if [ $? -ne 0 ] || [ -z "$REDIS_PASSWORD" ]; then
	echo "❌ Failed to generate REDIS_PASSWORD"
	exit 1
fi
echo "REDIS_PASSWORD=$REDIS_PASSWORD"
echo ""

echo "---"
echo "Copy these to your .env file"
echo "NEVER commit these values"
