#!/bin/bash

echo "🛑 Stopping Analytics AI Platform..."

# Function to clear default bucket contents
clear_default_bucket() {
    echo "🧹 Clearing default bucket contents..."
    
    # Check if gcloud is available and user is authenticated
    if command -v gcloud &> /dev/null; then
        # Check if user is authenticated
        if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
            # Clear the default bucket
            BUCKET_NAME="ai-analysis-default-bucket"
            echo "🗑️  Clearing bucket: gs://$BUCKET_NAME"
            
            # List files first
            FILES=$(gsutil ls gs://$BUCKET_NAME 2>/dev/null)
            if [ $? -eq 0 ] && [ -n "$FILES" ]; then
                echo "📁 Found files in bucket:"
                echo "$FILES"
                echo ""
                echo "🗑️  Deleting all files..."
                gsutil -m rm gs://$BUCKET_NAME/* 2>/dev/null
                if [ $? -eq 0 ]; then
                    echo "✅ Bucket cleared successfully"
                else
                    echo "⚠️  Some files may not have been deleted (this is normal if bucket is empty)"
                fi
            else
                echo "📭 Bucket is already empty"
            fi
        else
            echo "⚠️  Not authenticated with gcloud. Skipping bucket cleanup."
            echo "   Run 'gcloud auth login' to enable bucket cleanup."
        fi
    else
        echo "⚠️  gcloud CLI not found. Skipping bucket cleanup."
        echo "   Install Google Cloud SDK to enable bucket cleanup."
    fi
}

# Stop Docker services
docker-compose down

# Clear default bucket contents
clear_default_bucket

echo "✅ All services stopped and bucket cleared"