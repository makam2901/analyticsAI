#!/bin/bash

# Deployment script for Analytics AI Platform on Google Cloud Platform
# This script builds and deploys both frontend and backend to Cloud Run

set -e

# Configuration
PROJECT_ID=${PROJECT_ID}
REGION=${REGION:-"us-central1"}

echo "🚀 Deploying Analytics AI Platform to GCP Cloud Run"
echo "=================================================="
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Check if PROJECT_ID is set
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Please set PROJECT_ID environment variable"
    echo "   export PROJECT_ID=your-actual-project-id"
    exit 1
fi

# Set the project
echo "🔧 Setting GCP project..."
gcloud config set project $PROJECT_ID

# Configure Docker to use gcloud as a credential helper
echo "🔧 Configuring Docker authentication..."
gcloud auth configure-docker

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    secretmanager.googleapis.com \
    storage.googleapis.com

# Build and push Docker images
echo "🔨 Building and pushing Docker images..."

# Generate timestamp for unique tags (without cache busting)
TIMESTAMP=$(date +%s)
echo "Using timestamp: $TIMESTAMP for unique tags"

# Build and push backend image
echo "Building and pushing backend image..."
docker buildx build --platform linux/amd64 --load -f docker/Dockerfile.backend -t gcr.io/$PROJECT_ID/analytics-ai-backend:$TIMESTAMP .
docker tag gcr.io/$PROJECT_ID/analytics-ai-backend:$TIMESTAMP gcr.io/$PROJECT_ID/analytics-ai-backend:latest
docker push gcr.io/$PROJECT_ID/analytics-ai-backend:$TIMESTAMP
docker push gcr.io/$PROJECT_ID/analytics-ai-backend:latest

# Build and push frontend image with placeholder backend URL
echo "Building and pushing frontend image..."
BACKEND_URL_PLACEHOLDER="https://analytics-ai-backend-placeholder-uc.a.run.app"
docker buildx build --platform linux/amd64 --load -f docker/Dockerfile.frontend --build-arg BACKEND_URL=$BACKEND_URL_PLACEHOLDER -t gcr.io/$PROJECT_ID/analytics-ai-frontend:$TIMESTAMP .
docker tag gcr.io/$PROJECT_ID/analytics-ai-frontend:$TIMESTAMP gcr.io/$PROJECT_ID/analytics-ai-frontend:latest
docker push gcr.io/$PROJECT_ID/analytics-ai-frontend:$TIMESTAMP
docker push gcr.io/$PROJECT_ID/analytics-ai-frontend:latest

# Create secrets (if they don't exist)
echo "🔐 Setting up secrets..."
./deployment/scripts/create-secrets.sh

# Grant Cloud Run service account access to secrets
echo "🔐 Setting up IAM permissions for secrets..."

# Get the default compute service account (proper format)
COMPUTE_SA=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")-compute@developer.gserviceaccount.com
echo "Using service account: $COMPUTE_SA"

# Grant Secret Manager Secret Accessor role to the default compute service account
gcloud secrets add-iam-policy-binding gemini-api-key \
    --member="serviceAccount:$COMPUTE_SA" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID

gcloud secrets add-iam-policy-binding jwt-secret \
    --member="serviceAccount:$COMPUTE_SA" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID

# Grant Cloud Run service account access to GCS buckets
echo "🔐 Setting up GCS permissions..."
gsutil iam ch serviceAccount:$COMPUTE_SA:objectAdmin gs://ai-analysis-default-bucket 2>/dev/null || echo "Bucket ai-analysis-default-bucket permissions updated or bucket doesn't exist"
gsutil iam ch serviceAccount:$COMPUTE_SA:objectAdmin gs://sample-bucket-v2901 2>/dev/null || echo "Bucket sample-bucket-v2901 permissions updated or bucket doesn't exist"

echo "✅ IAM permissions configured"

# Update Cloud Run configurations with actual PROJECT_ID
echo "Updating Cloud Run configurations..."

# Update backend configuration
sed "s/PROJECT_ID/$PROJECT_ID/g" deployment/cloud-run/backend-service.yaml > deployment/cloud-run/backend-service-deploy.yaml

# Deploy backend to Cloud Run
echo "🚀 Deploying backend to Cloud Run..."
gcloud run services replace deployment/cloud-run/backend-service-deploy.yaml --region=$REGION

# Force update to ensure new image is used
echo "Forcing backend service update..."
gcloud run services update analytics-ai-backend --region=$REGION --image=gcr.io/$PROJECT_ID/analytics-ai-backend:latest

# Wait a moment for the service to be fully ready
echo "Waiting for backend service to be ready..."
sleep 10

# Get backend URL
BACKEND_URL=$(gcloud run services describe analytics-ai-backend --region=$REGION --format="value(status.url)")
echo "Backend deployed successfully!"

# Verify the URL is valid
if [[ -z "$BACKEND_URL" || "$BACKEND_URL" == "None" ]]; then
    echo "Error: Could not get backend URL"
    exit 1
fi

# Rebuild frontend image with correct backend URL
echo "🔄 Rebuilding frontend with correct backend URL: $BACKEND_URL"
NEW_TIMESTAMP=$(date +%s)
docker buildx build --platform linux/amd64 --load -f docker/Dockerfile.frontend --build-arg BACKEND_URL=$BACKEND_URL -t gcr.io/$PROJECT_ID/analytics-ai-frontend:$NEW_TIMESTAMP .
docker tag gcr.io/$PROJECT_ID/analytics-ai-frontend:$NEW_TIMESTAMP gcr.io/$PROJECT_ID/analytics-ai-frontend:latest
docker push gcr.io/$PROJECT_ID/analytics-ai-frontend:$NEW_TIMESTAMP
docker push gcr.io/$PROJECT_ID/analytics-ai-frontend:latest

# Update frontend configuration with backend URL
echo "Updating frontend configuration with backend URL: $BACKEND_URL"
sed "s/PROJECT_ID/$PROJECT_ID/g" deployment/cloud-run/frontend-service.yaml > deployment/cloud-run/frontend-service-deploy.yaml

# Deploy frontend to Cloud Run
echo "🚀 Deploying frontend to Cloud Run..."
gcloud run services replace deployment/cloud-run/frontend-service-deploy.yaml --region=$REGION

# Force update to ensure new image is used
echo "Forcing frontend service update..."
gcloud run services update analytics-ai-frontend --region=$REGION --image=gcr.io/$PROJECT_ID/analytics-ai-frontend:latest

# Wait a moment for the service to be fully ready
echo "Waiting for frontend service to be ready..."
sleep 10

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
# Verify the URL is valid
if [[ -z "$FRONTEND_URL" || "$FRONTEND_URL" == "None" ]]; then
    echo "Error: Could not get frontend URL"
    exit 1
fi

# Clean up temporary files
rm -f deployment/cloud-run/backend-service-deploy.yaml deployment/cloud-run/frontend-service-deploy.yaml

# Configure IAM policies for public access
echo "Configuring IAM policies for public access..."
gcloud run services add-iam-policy-binding analytics-ai-frontend \
    --region=$REGION \
    --member="allUsers" \
    --role="roles/run.invoker"

gcloud run services add-iam-policy-binding analytics-ai-backend \
    --region=$REGION \
    --member="allUsers" \
    --role="roles/run.invoker"

# Update CORS settings for backend
echo "Configuring CORS settings..."
echo "Setting CORS_ORIGINS to: $FRONTEND_URL"
gcloud run services update analytics-ai-backend \
    --region=$REGION \
    --set-env-vars="CORS_ORIGINS=$FRONTEND_URL"

echo "🛑 To delete deployment:"
echo "   gcloud run services delete analytics-ai-backend --region $REGION"
echo "   gcloud run services delete analytics-ai-frontend --region $REGION"
echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📱 Your Application URLs (these URLs remain stable):"
echo "Frontend: $FRONTEND_URL"
echo "Backend:  $BACKEND_URL"
echo ""
echo "✅ Configuration:"
echo "   • CORS configured correctly"
echo "   • IAM policies set for public access"
echo "   • Cost optimization enabled"
echo ""
echo "🔗 Test your application: $FRONTEND_URL"
