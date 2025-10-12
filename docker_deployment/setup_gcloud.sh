#!/bin/bash

# Google Cloud Setup Script for Analytics AI
# This script sets up Application Default Credentials for the application

echo "🚀 Setting up Google Cloud authentication for Analytics AI..."

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first:"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Login to Google Cloud
echo "🔐 Logging into Google Cloud..."
gcloud auth login

# Set the project
echo "📁 Setting project to ai-analysis-v1..."
gcloud config set project ai-analysis-v1

# Enable Application Default Credentials
echo "🔑 Setting up Application Default Credentials..."
gcloud auth application-default login

# Verify setup
echo "✅ Verifying setup..."
echo "Current project: $(gcloud config get-value project)"
echo "Authenticated accounts:"
gcloud auth list

echo ""
echo "🎉 Setup complete! You can now run the application with:"
echo "   docker-compose up"
echo ""
echo "The application will use your Google Cloud credentials automatically."

