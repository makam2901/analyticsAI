#!/bin/bash

# Complete setup script for Analytics AI Platform
# This script handles everything from start to finish with user prompts

set -e

echo "🚀 Analytics AI Platform - Complete GCP Setup"
echo "=============================================="
echo ""

# Function to prompt for required information
prompt_for_info() {
    echo "📋 Let's gather the required information..."
    echo ""
    
    # Prompt for Project ID
    if [ -z "$PROJECT_ID" ]; then
        read -p "🔧 Enter your GCP Project ID: " PROJECT_ID
        if [ -z "$PROJECT_ID" ]; then
            echo "❌ Error: Project ID is required"
            exit 1
        fi
    else
        echo "✅ Project ID already set: $PROJECT_ID"
    fi
    
    # Prompt for Gemini API Key
    if [ -z "$GEMINI_API_KEY" ]; then
        echo ""
        echo "🔑 Enter your Gemini API Key:"
        echo "   (You can get this from: https://makersuite.google.com/app/apikey)"
        read -s -p "   Gemini API Key: " GEMINI_API_KEY
        echo ""
        if [ -z "$GEMINI_API_KEY" ]; then
            echo "❌ Error: Gemini API Key is required"
            exit 1
        fi
    else
        echo "✅ Gemini API Key already set: ${GEMINI_API_KEY:0:20}..."
    fi
    
    # Prompt for JWT Secret (optional)
    if [ -z "$JWT_SECRET" ]; then
        echo ""
        echo "🔐 Enter your JWT Secret (or press Enter for auto-generated):"
        read -s -p "   JWT Secret: " JWT_SECRET
        echo ""
        if [ -z "$JWT_SECRET" ]; then
            # Generate a random JWT secret
            JWT_SECRET=$(openssl rand -base64 32 2>/dev/null || echo "analytics_ai_jwt_secret_$(date +%s)")
            echo "✅ Auto-generated JWT Secret: ${JWT_SECRET:0:20}..."
        fi
    else
        echo "✅ JWT Secret already set: ${JWT_SECRET:0:20}..."
    fi
    
    echo ""
    echo "📋 Configuration Summary:"
    echo "Project ID: $PROJECT_ID"
    echo "Gemini API Key: ${GEMINI_API_KEY:0:20}..."
    echo "JWT Secret: ${JWT_SECRET:0:20}..."
    echo ""
}

# Function to check authentication
check_auth() {
    echo "🔐 Checking GCP authentication..."
    
    # Check if gcloud is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        echo "❌ Not authenticated with gcloud"
        echo "Please run: gcloud auth login"
        exit 1
    fi
    
    # Set the project
    gcloud config set project $PROJECT_ID
    
    echo "✅ Authentication verified"
    echo ""
}

# Function to show main menu
show_menu() {
    echo "🔧 What would you like to do?"
    echo "1. 🏗️  Complete Setup (Infrastructure + Deploy)"
    echo "2. 🏗️  Setup Infrastructure Only (secrets, APIs, permissions)"
    echo "3. 🚀 Deploy Application Only (rebuilds both frontend & backend with latest code)"
    echo "4. 🧪 Test Local Setup (start Docker containers locally)"
    echo "5. 🧹 Clean Everything (remove all resources)"
    echo "6. 📊 Show Application URLs"
    echo "7. ❌ Exit"
    echo ""
    read -p "Choose an option (1-7): " choice
}

# Function to run complete setup
complete_setup() {
    echo "🏗️  Running complete setup..."
    echo ""
    
    # Setup infrastructure
    echo "Step 1/3: Setting up infrastructure..."
    echo "   This will create secrets, enable APIs, and set permissions"
    PROJECT_ID=$PROJECT_ID GEMINI_API_KEY=$GEMINI_API_KEY JWT_SECRET=$JWT_SECRET ./deployment/scripts/create-secrets.sh
    
    echo ""
    echo "Step 2/3: Deploying application..."
    PROJECT_ID=$PROJECT_ID ./deployment/scripts/deploy.sh
    
    echo ""
    echo "Step 3/3: Setup complete!"
    
    # Get URLs
    echo ""
    echo "🎉 Deployment completed successfully!"
    echo ""
    show_urls
}

# Function to show application URLs
show_urls() {
    echo "📱 Your application URLs:"
    BACKEND_URL=$(gcloud run services describe analytics-ai-backend --region=us-central1 --format="value(status.url)" 2>/dev/null || echo "Not available")
    FRONTEND_URL=$(gcloud run services describe analytics-ai-frontend --region=us-central1 --format="value(status.url)" 2>/dev/null || echo "Not available")
    
    if [ "$BACKEND_URL" != "Not available" ] && [ "$FRONTEND_URL" != "Not available" ]; then
        echo "🌐 Frontend: $FRONTEND_URL"
        echo "🔗 Backend API: $BACKEND_URL"
        echo "📖 API Documentation: $BACKEND_URL/api/docs"
        echo ""
        echo "🎯 Start using your Analytics AI Platform!"
        echo "   Open the Frontend URL in your browser to begin"
    else
        echo "⚠️  Services not yet deployed or not accessible"
        echo "   Run option 1 (Complete Setup) or option 3 (Deploy Only) first"
    fi
    echo ""
}

# Function to test local setup
test_local_setup() {
    echo "🧪 Testing local Docker setup..."
    echo ""
    
    # Check if .env file exists
    if [ ! -f "config/.env" ]; then
        echo "📝 Creating local environment file..."
        cp config/env.example config/.env
        echo "✅ Created config/.env from template"
        echo "⚠️  Please edit config/.env with your actual API keys before continuing"
        echo ""
        read -p "Press Enter when you've updated config/.env with your API keys..."
    fi
    
    echo "🚀 Starting local Docker containers..."
    ./scripts/start.sh
    
    echo ""
    echo "✅ Local setup is working!"
    echo ""
    echo "📱 Your local application URLs:"
    echo "🌐 Frontend: http://localhost:3000"
    echo "🔗 Backend API: http://localhost:8000"
    echo "📖 API Documentation: http://localhost:8000/api/docs"
    echo ""
    echo "🛑 To stop local containers: ./scripts/stop.sh"
    echo "📋 To view logs: ./scripts/logs.sh"
    echo ""
}

# Function to clean everything
clean_everything() {
    echo "🧹 Cleaning up all resources..."
    echo ""
    echo "⚠️  WARNING: This will delete ALL resources including:"
    echo "   - All Cloud Run services"
    echo "   - All Docker images in Container Registry"
    echo "   - All secrets in Secret Manager"
    echo ""
    echo "🔧 Cleanup options:"
    echo "1. Clean everything (Cloud Run + Container Registry + Secrets)"
    echo "2. Clean Cloud Run services only (keep images and secrets)"
    echo "3. Cancel cleanup"
    echo ""
    read -p "Choose cleanup option (1-3): " cleanup_choice
    
    case $cleanup_choice in
        1)
            echo ""
            read -p "Are you sure you want to delete EVERYTHING? Type 'yes' to confirm: " confirm
            if [ "$confirm" = "yes" ]; then
                echo "🗑️  Deleting Cloud Run services..."
                gcloud run services delete analytics-ai-backend --region=us-central1 --quiet 2>/dev/null || true
                gcloud run services delete analytics-ai-frontend --region=us-central1 --quiet 2>/dev/null || true
                
                echo "🗑️  Deleting Container Registry images..."
                gcloud container images delete gcr.io/$PROJECT_ID/analytics-ai-backend --quiet 2>/dev/null || true
                gcloud container images delete gcr.io/$PROJECT_ID/analytics-ai-frontend --quiet 2>/dev/null || true
                
                echo "🗑️  Deleting secrets..."
                gcloud secrets delete gemini-api-key --quiet 2>/dev/null || true
                gcloud secrets delete jwt-secret --quiet 2>/dev/null || true
                
                echo ""
                echo "✅ Complete cleanup completed successfully!"
                echo ""
                echo "🔧 Next steps:"
                echo "   Run this script again and choose option 1 for complete setup"
                echo "   Or choose option 2 to setup infrastructure only"
                echo ""
            else
                echo "❌ Cleanup cancelled."
            fi
            ;;
        2)
            echo ""
            read -p "Are you sure you want to clean Cloud Run services? Type 'yes' to confirm: " confirm
            if [ "$confirm" = "yes" ]; then
                echo "🗑️  Deleting Cloud Run services..."
                gcloud run services delete analytics-ai-backend --region=us-central1 --quiet 2>/dev/null || true
                gcloud run services delete analytics-ai-frontend --region=us-central1 --quiet 2>/dev/null || true
                
                echo ""
                echo "✅ Cloud Run cleanup completed successfully!"
                echo "📦 Container Registry images and secrets have been preserved"
                echo ""
                echo "🔧 Next steps:"
                echo "   Run this script again and choose option 3 to redeploy"
                echo "   Or choose option 1 for complete setup"
                echo ""
            else
                echo "❌ Cleanup cancelled."
            fi
            ;;
        3)
            echo "❌ Cleanup cancelled."
            ;;
        *)
            echo "❌ Invalid option. Cleanup cancelled."
            ;;
    esac
}

# Function to check prerequisites
check_prerequisites() {
    echo "🔍 Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        echo "❌ Google Cloud SDK (gcloud) is not installed"
        echo "   Please install it from: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker is not installed"
        echo "   Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
        exit 1
    fi
    
    # Check if docker is running
    if ! docker info &> /dev/null; then
        echo "❌ Docker is not running"
        echo "   Please start Docker Desktop and try again"
        exit 1
    fi
    
    echo "✅ All prerequisites are met"
    echo ""
}

# Main execution
main() {
    # Check prerequisites
    check_prerequisites
    
    # Prompt for required information
    prompt_for_info
    
    # Check authentication
    check_auth
    
    # Show menu and handle choice
    while true; do
        show_menu
        
        case $choice in
            1)
                complete_setup
                break
                ;;
            2)
                echo "🏗️  Setting up infrastructure..."
                echo "   This will create secrets, enable APIs, and set permissions"
                PROJECT_ID=$PROJECT_ID GEMINI_API_KEY=$GEMINI_API_KEY JWT_SECRET=$JWT_SECRET ./deployment/scripts/create-secrets.sh
                echo ""
                echo "✅ Infrastructure setup completed!"
                echo ""
                echo "🔧 Next steps:"
                echo "   Run this script again and choose option 3 to deploy the application"
                echo "   Or choose option 1 for complete setup"
                echo ""
                break
                ;;
            3)
                echo "🚀 Deploying application with latest code changes..."
                echo "   This will rebuild and deploy both frontend and backend"
                echo "   with all your latest code changes."
                echo ""
                PROJECT_ID=$PROJECT_ID ./deployment/scripts/deploy.sh
                echo ""
                echo "✅ Application deployed successfully!"
                echo ""
                show_urls
                break
                ;;
            4)
                test_local_setup
                break
                ;;
            5)
                clean_everything
                break
                ;;
            6)
                show_urls
                break
                ;;
            7)
                echo "👋 Goodbye!"
                exit 0
                ;;
            *)
                echo "❌ Invalid option. Please choose 1-7."
                echo ""
                ;;
        esac
    done
    
    echo ""
    echo "📖 For more information, see README.md"
    echo ""
    echo "💡 Tip: Run this script anytime to manage your application!"
    echo "   ./setup.sh"
}

# Run main function
main
