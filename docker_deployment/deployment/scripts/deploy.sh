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

# Generate timestamp for unique tags
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Build and push backend image
echo "Building backend image..."
docker buildx build --platform linux/amd64 --load --no-cache -f docker/Dockerfile.backend -t gcr.io/$PROJECT_ID/analytics-ai-backend:$TIMESTAMP .
docker tag gcr.io/$PROJECT_ID/analytics-ai-backend:$TIMESTAMP gcr.io/$PROJECT_ID/analytics-ai-backend:latest
docker push gcr.io/$PROJECT_ID/analytics-ai-backend:$TIMESTAMP
docker push gcr.io/$PROJECT_ID/analytics-ai-backend:latest

# Build and push frontend image (will be updated with backend URL after backend deployment)
echo "Building frontend image..."
docker buildx build --platform linux/amd64 --load --no-cache -f docker/Dockerfile.frontend --build-arg BACKEND_URL=http://localhost:8000 -t gcr.io/$PROJECT_ID/analytics-ai-frontend:$TIMESTAMP .
docker tag gcr.io/$PROJECT_ID/analytics-ai-frontend:$TIMESTAMP gcr.io/$PROJECT_ID/analytics-ai-frontend:latest
docker push gcr.io/$PROJECT_ID/analytics-ai-frontend:$TIMESTAMP
docker push gcr.io/$PROJECT_ID/analytics-ai-frontend:latest

# Create secrets (if they don't exist)
echo "🔐 Setting up secrets..."
./deployment/scripts/create-secrets.sh

# Grant Cloud Run service account access to secrets
echo "🔐 Setting up IAM permissions for secrets..."
SERVICE_ACCOUNT="${PROJECT_ID}-compute@developer.gserviceaccount.com"

# Grant Secret Manager Secret Accessor role to the default compute service account
gcloud secrets add-iam-policy-binding gemini-api-key \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID

gcloud secrets add-iam-policy-binding jwt-secret \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID

echo "✅ IAM permissions configured"

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
        --set-env-vars "DATABASE_PATH=/tmp/analytics_ai.db,PYTHONPATH=/app,PROJECT_ID=$PROJECT_ID,DEFAULT_BUCKET=ai-analysis-default-bucket,NODE_ENV=production" \
    --set-secrets "GEMINI_API_KEY=gemini-api-key:latest,JWT_SECRET=jwt-secret:latest"

# Wait for backend deployment to complete
echo "⏳ Waiting for backend deployment to complete..."
sleep 30

# Get backend URL
BACKEND_URL=$(gcloud run services describe analytics-ai-backend --platform managed --region $REGION --format 'value(status.url)')
echo "Backend URL: $BACKEND_URL"

# Rebuild frontend image with correct backend URL
echo "🔄 Rebuilding frontend with correct backend URL..."
NEW_TIMESTAMP=$(date +%Y%m%d-%H%M%S)
docker buildx build --platform linux/amd64 --load --no-cache -f docker/Dockerfile.frontend --build-arg BACKEND_URL=$BACKEND_URL -t gcr.io/$PROJECT_ID/analytics-ai-frontend:$NEW_TIMESTAMP .
docker tag gcr.io/$PROJECT_ID/analytics-ai-frontend:$NEW_TIMESTAMP gcr.io/$PROJECT_ID/analytics-ai-frontend:latest
docker push gcr.io/$PROJECT_ID/analytics-ai-frontend:$NEW_TIMESTAMP
docker push gcr.io/$PROJECT_ID/analytics-ai-frontend:latest

# Deploy frontend service
echo "🚀 Deploying frontend service..."
gcloud run deploy analytics-ai-frontend \
    --image gcr.io/$PROJECT_ID/analytics-ai-frontend \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 10

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
