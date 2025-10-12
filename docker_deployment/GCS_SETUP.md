# Google Cloud Storage Setup - Hybrid Access Mode

This application supports **both public bucket browsing and private file uploads** for comprehensive data management.

## 🚀 How It Works

### Dual Data Sources
1. **Public Buckets** - Browse and preview files from any public GCS bucket (read-only)
2. **Default Bucket** - Upload and manage your own files (read/write access)

### User Experience
- **Connect to Public Bucket**: Paste any public bucket URL (e.g., `gs://cloud-samples-data`)
- **Upload Your Files**: Upload files to your personal space in the default bucket
- **Combined View**: See files from both sources together in one interface
- **Source Indicators**: Clear visual distinction between uploaded and public files

## Setup Requirements

### For Public Bucket Access (No Setup Required)
- **Anonymous access** - Works immediately
- **No authentication** - Users just paste bucket URLs
- **Read-only** - Browse and preview files

### For File Uploads (Requires Setup)
- **Service account credentials** needed for default bucket uploads
- **Authenticated access** for write operations

## Authentication Setup

### Simple Setup with Application Default Credentials

Since you're already logged into Google Cloud via terminal, we can use **Application Default Credentials (ADC)** - no service account keys needed!

### Step 1: Login to Google Cloud
```bash
# Login to your Google Cloud account
gcloud auth login

# Set your project
gcloud config set project ai-analysis-v1

# Enable Application Default Credentials
gcloud auth application-default login
```

### Step 2: Docker Configuration
The docker-compose.yml is configured to:
- Mount your local gcloud config: `~/.config/gcloud:/root/.config/gcloud`
- Use your existing authentication automatically
- No service account keys or credential files needed

### Step 3: Verify Setup
```bash
# Test that authentication works
gcloud auth list
gcloud config get-value project
```

## Features Available

### ✅ Public Bucket Features (No Auth Required)
- **Browse any public bucket** - Paste bucket URL and explore files
- **File preview** - See first few records of CSV/JSON files
- **File information** - View file size, type, and modification date
- **Anonymous access** - Works without any setup

### ✅ Default Bucket Features (Auth Required)
- **File uploads** - Upload CSV, JSON, XLSX, Parquet files
- **File management** - Your personal data space
- **File preview** - Preview your uploaded files
- **Combined view** - See uploaded files alongside public bucket files

### 🎯 Combined Experience
- **Unified interface** - All files displayed together as data cards
- **Source indicators** - Green badges for uploaded files, blue for public files
- **Smart preview** - Automatically determines correct bucket for file preview
- **Data summary** - Shows count of uploaded vs public files

## Public Buckets to Try

- `gs://cloud-samples-data` - Google Cloud sample datasets
- `gs://bigquery-public-data` - Public BigQuery datasets
- `gs://gcp-public-data-*` - Various Google Cloud public data buckets
- Any other publicly accessible GCS bucket

## Development Scripts

### Start Application
```bash
./start.sh
```

### Stop Application & Clear Bucket
```bash
./stop.sh
```
This will:
- Stop all Docker services
- Automatically clear the default bucket contents
- Keep your development environment clean

### Clear Bucket Only
```bash
./clear_bucket.sh
```
This will:
- Ask for confirmation before deleting files
- Clear only the default bucket contents
- Keep the application running

## Technical Implementation

The application uses a hybrid approach:
- **Anonymous client** for public bucket access
- **Authenticated client** for default bucket uploads
- **Combined API endpoint** to merge files from both sources
- **Source tracking** to identify file origins
- **Automatic cleanup** scripts for development convenience

## Features

### Data Tab Functionality

1. **Connect Existing Bucket**: Users can provide a GCS bucket URL (gs://bucket-name) to browse files
2. **Use Default Bucket**: Users can upload files to the managed default bucket (ai-analysis-default-bucket)
3. **File Preview**: Click on any data file to see a preview of the first few records
4. **File Upload**: Upload CSV, JSON, XLSX, or Parquet files to the default bucket

### Supported File Types

- **CSV**: Shows first 10 rows in a formatted table
- **JSON**: Shows first 10 objects with proper formatting
- **Other formats**: Shows raw text preview

### API Endpoints

- `GET /api/data/bucket/{bucket_name}/files` - List files in a bucket
- `GET /api/data/default-bucket/files` - List files in default bucket
- `GET /api/data/bucket/{bucket_name}/file/{file_name}/preview` - Preview file content
- `POST /api/data/default-bucket/upload` - Upload file to default bucket
- `DELETE /api/data/bucket/{bucket_name}/file/{file_name}` - Delete a file

## Usage

1. After login/guest access, navigate to the **Data** tab
2. Choose between connecting to an existing bucket or using the default bucket
3. Browse files as data cards with file information
4. Click on any file to preview its contents
5. For default bucket, use the "Upload Files" button to add new data files
