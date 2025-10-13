#!/bin/bash

# GCP Cloud Run Deployment Script
# Make sure to set your PROJECT_ID before running

set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-"your-project-id"}
REGION=${REGION:-"us-central1"}
SERVICE_ACCOUNT=${SERVICE_ACCOUNT:-"analytics-ai-sa@${PROJECT_ID}.iam.gserviceaccount.com"}

echo "🚀 Deploying Analytics AI Platform to GCP Cloud Run"
echo "=================================================="
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Check if PROJECT_ID is set
if [ "$PROJECT_ID" = "your-project-id" ]; then
    echo "❌ Please set PROJECT_ID environment variable"
    echo "   export PROJECT_ID=your-actual-project-id"
    exit 1
fi

# Set the project
echo "🔧 Setting GCP project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    secretmanager.googleapis.com \
    storage.googleapis.com

# Build and push Docker images
echo "🔨 Building and pushing Docker images..."

# Build backend image
echo "Building backend image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/analytics-ai-backend ./docker --file ./docker/Dockerfile.backend

# Build frontend image  
echo "Building frontend image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/analytics-ai-frontend ./docker --file ./docker/Dockerfile.frontend

# Create secrets (if they don't exist)
echo "🔐 Setting up secrets..."
./deployment/scripts/create-secrets.sh

# Deploy backend service
echo "🚀 Deploying backend service..."
gcloud run deploy analytics-ai-backend \
    --image gcr.io/$PROJECT_ID/analytics-ai-backend \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --max-instances 10 \
    --set-env-vars "DATABASE_PATH=/tmp/analytics_ai.db,PYTHONPATH=/app,PROJECT_ID=$PROJECT_ID,DEFAULT_BUCKET=ai-analysis-default-bucket,NODE_ENV=production,PORT=8000" \
    --set-secrets "GEMINI_API_KEY=gemini-api-key:latest,JWT_SECRET=jwt-secret:latest"

# Get backend URL
BACKEND_URL=$(gcloud run services describe analytics-ai-backend --platform managed --region $REGION --format 'value(status.url)')
echo "Backend URL: $BACKEND_URL"

# Deploy frontend service
echo "🚀 Deploying frontend service..."
gcloud run deploy analytics-ai-frontend \
    --image gcr.io/$PROJECT_ID/analytics-ai-frontend \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 10 \
    --set-env-vars "BACKEND_URL=$BACKEND_URL"

# Get frontend URL
FRONTEND_URL=$(gcloud run services describe analytics-ai-frontend --platform managed --region $REGION --format 'value(status.url)')

echo ""
echo "✅ Deployment Complete!"
echo "======================"
echo "🌐 Frontend: $FRONTEND_URL"
echo "🔗 Backend API: $BACKEND_URL"
echo "📖 API Documentation: $BACKEND_URL/api/docs"
echo ""
echo "🔐 Secrets created:"
echo "   - gemini-api-key"
echo "   - jwt-secret"
echo ""
echo "🛑 To delete deployment:"
echo "   gcloud run services delete analytics-ai-backend --region $REGION"
echo "   gcloud run services delete analytics-ai-frontend --region $REGION"
