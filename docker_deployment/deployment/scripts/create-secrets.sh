#!/bin/bash

# Script to create secrets in Google Secret Manager
# Run this before deploying to Cloud Run

set -e

PROJECT_ID=${PROJECT_ID:-"your-project-id"}

echo "🔐 Creating secrets in Google Secret Manager"
echo "============================================"

# Check if PROJECT_ID is set
if [ "$PROJECT_ID" = "your-project-id" ]; then
    echo "❌ Please set PROJECT_ID environment variable"
    echo "   export PROJECT_ID=your-actual-project-id"
    exit 1
fi

# Enable Secret Manager API
echo "🔧 Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID

# Create GEMINI_API_KEY secret
echo "🔐 Creating GEMINI_API_KEY secret..."
if ! gcloud secrets describe gemini-api-key --project=$PROJECT_ID >/dev/null 2>&1; then
    echo "Please enter your GEMINI_API_KEY:"
    read -s GEMINI_API_KEY
    echo -n "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key \
        --data-file=- \
        --project=$PROJECT_ID
    echo "✅ GEMINI_API_KEY secret created"
else
    echo "⚠️  GEMINI_API_KEY secret already exists"
fi

# Create JWT_SECRET
echo "🔐 Creating JWT_SECRET..."
if ! gcloud secrets describe jwt-secret --project=$PROJECT_ID >/dev/null 2>&1; then
    # Generate a random JWT secret
    JWT_SECRET=$(openssl rand -base64 32)
    echo -n "$JWT_SECRET" | gcloud secrets create jwt-secret \
        --data-file=- \
        --project=$PROJECT_ID
    echo "✅ JWT_SECRET created with random value"
else
    echo "⚠️  JWT_SECRET already exists"
fi

echo ""
echo "✅ All secrets created successfully!"
echo ""
echo "📋 Created secrets:"
echo "   - gemini-api-key"
echo "   - jwt-secret"
echo ""
echo "🔍 To view secrets:"
echo "   gcloud secrets list --project=$PROJECT_ID"
echo ""
echo "🔐 To update a secret:"
echo "   echo 'new-value' | gcloud secrets versions add secret-name --data-file=- --project=$PROJECT_ID"
