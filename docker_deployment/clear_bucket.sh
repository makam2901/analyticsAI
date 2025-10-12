#!/bin/bash

echo "🧹 Clearing Default Bucket Contents"
echo "=================================="

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
                
                # Ask for confirmation
                read -p "❓ Are you sure you want to delete all files? (y/N): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    echo "🗑️  Deleting all files..."
                    gsutil -m rm gs://$BUCKET_NAME/* 2>/dev/null
                    if [ $? -eq 0 ]; then
                        echo "✅ Bucket cleared successfully"
                    else
                        echo "⚠️  Some files may not have been deleted"
                    fi
                else
                    echo "❌ Operation cancelled"
                fi
            else
                echo "📭 Bucket is already empty"
            fi
        else
            echo "⚠️  Not authenticated with gcloud."
            echo "   Run 'gcloud auth login' to enable bucket cleanup."
            exit 1
        fi
    else
        echo "⚠️  gcloud CLI not found."
        echo "   Install Google Cloud SDK to enable bucket cleanup."
        exit 1
    fi
}

clear_default_bucket

