from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from typing import List, Dict, Any
import os
import io
import pandas as pd
from google.cloud import storage
from google.auth import default
import json

router = APIRouter()

# GCS Configuration
PROJECT_ID = os.getenv("PROJECT_ID", "ai-analysis-v1")
DEFAULT_BUCKET = os.getenv("DEFAULT_BUCKET", "ai-analysis-default-bucket")

def get_gcs_client():
    """Get GCS client using Application Default Credentials"""
    try:
        # Use Application Default Credentials (from gcloud auth login)
        credentials, project = default()
        client = storage.Client(credentials=credentials, project=project)
        return client
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize GCS client. Make sure you're logged in with 'gcloud auth login': {str(e)}")

@router.get("/sources")
def get_data_sources():
    # This endpoint is now a placeholder and returns an empty list
    # as per your request to remove sample data.
    return []

@router.get("/bucket/{bucket_name}/files")
async def get_bucket_files(bucket_name: str):
    """Get all files from a GCS bucket"""
    try:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)
        
        # Check if bucket exists
        if not bucket.exists():
            raise HTTPException(status_code=404, detail=f"Bucket '{bucket_name}' not found")
        
        files = []
        for blob in bucket.list_blobs():
            files.append({
                "name": blob.name,
                "size": blob.size,
                "contentType": blob.content_type,
                "updated": blob.updated.strftime("%Y-%m-%d %H:%M:%S") if blob.updated else None,
                "created": blob.time_created.strftime("%Y-%m-%d %H:%M:%S") if blob.time_created else None
            })
        
        return files
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@router.get("/default-bucket/files")
async def get_default_bucket_files():
    """Get all files from the default bucket"""
    return await get_bucket_files(DEFAULT_BUCKET)

@router.get("/combined-files")
async def get_combined_files(public_bucket: str = None):
    """Get files from both public bucket and default bucket combined - only when public_bucket is specified"""
    try:
        combined_files = []
        
        # Only get files from default bucket if we have a public bucket connection
        # This prevents showing files when user just wants to upload
        if public_bucket:
            # Get files from default bucket (uploaded files)
            try:
                default_files = await get_bucket_files(DEFAULT_BUCKET)
                for file in default_files:
                    file["source"] = "uploaded"
                    file["bucket"] = DEFAULT_BUCKET
                    file["source_info"] = "Your uploaded files"
                    combined_files.append(file)
            except Exception as e:
                # Default bucket might not exist or be accessible
                pass
            
            # Get files from public bucket if different from default bucket
            if public_bucket != DEFAULT_BUCKET:
                try:
                    public_files = await get_bucket_files(public_bucket)
                    for file in public_files:
                        # Check if this file already exists as an uploaded file (uploaded files take priority)
                        existing_file = next((f for f in combined_files if f["name"] == file["name"]), None)
                        if not existing_file:
                            file["source"] = "public"
                            file["bucket"] = public_bucket
                            file["source_info"] = f"Public bucket: {public_bucket}"
                            combined_files.append(file)
                except Exception as e:
                    # Public bucket might not be accessible
                    pass
        
        return combined_files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get combined files: {str(e)}")

@router.get("/bucket/{bucket_name}/file/{file_name}/preview")
async def preview_file(bucket_name: str, file_name: str, rows: int = 10):
    """Preview first few rows of a file"""
    try:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        
        if not blob.exists():
            raise HTTPException(status_code=404, detail=f"File '{file_name}' not found in bucket '{bucket_name}'")
        
        # Download file content
        content = blob.download_as_text()
        
        # Determine file type and parse accordingly
        file_extension = file_name.lower().split('.')[-1]
        
        if file_extension == 'csv':
            df = pd.read_csv(io.StringIO(content))
            
            # Convert to structured format for better frontend handling
            preview_rows = df.head(rows).to_dict('records')
            columns_info = []
            
            for col in df.columns:
                col_data = df[col]
                dtype = str(col_data.dtype)
                
                # Map pandas dtypes to more readable types
                if dtype.startswith('int'):
                    data_type = 'int'
                elif dtype.startswith('float'):
                    data_type = 'float'
                elif dtype.startswith('bool'):
                    data_type = 'bool'
                elif dtype.startswith('datetime'):
                    data_type = 'date'
                else:
                    data_type = 'string'
                
                columns_info.append({
                    "name": col,
                    "type": data_type,
                    "dtype": dtype
                })
            
            return {
                "type": "csv",
                "columns": columns_info,
                "rows": preview_rows,
                "rowsShown": min(rows, len(df)),
                "totalRows": len(df)
            }
        
        elif file_extension == 'json':
            try:
                json_data = json.loads(content)
                if isinstance(json_data, list):
                    # Convert JSON array to DataFrame for consistent handling
                    df = pd.DataFrame(json_data[:rows])
                    preview_rows = df.to_dict('records')
                    total_rows = len(json_data)
                    
                    # Get column info
                    columns_info = []
                    for col in df.columns:
                        col_data = df[col]
                        dtype = str(col_data.dtype)
                        
                        if dtype.startswith('int'):
                            data_type = 'int'
                        elif dtype.startswith('float'):
                            data_type = 'float'
                        elif dtype.startswith('bool'):
                            data_type = 'bool'
                        elif dtype.startswith('datetime'):
                            data_type = 'date'
                        else:
                            data_type = 'string'
                        
                        columns_info.append({
                            "name": col,
                            "type": data_type,
                            "dtype": dtype
                        })
                else:
                    # Single JSON object
                    preview_rows = [json_data]
                    columns_info = [{"name": "data", "type": "json", "dtype": "object"}]
                    total_rows = 1
                
                return {
                    "type": "json",
                    "columns": columns_info,
                    "rows": preview_rows,
                    "rowsShown": len(preview_rows),
                    "totalRows": total_rows
                }
            except json.JSONDecodeError:
                return {
                    "type": "json",
                    "data": content[:1000] + "..." if len(content) > 1000 else content,
                    "rowsShown": 0,
                    "totalRows": 0,
                    "error": "Invalid JSON format"
                }
        
        else:
            # For other file types, return raw text preview
            preview_data = content[:2000] + "..." if len(content) > 2000 else content
            return {
                "type": file_extension,
                "data": preview_data,
                "rowsShown": 0,
                "totalRows": 0,
                "message": f"Raw preview of {file_extension} file"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to preview file: {str(e)}")

@router.post("/default-bucket/upload")
async def upload_to_default_bucket(file: UploadFile = File(...)):
    """Upload a file to the default bucket"""
    try:
        # Validate filename
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Upload file content first to check size
        content = await file.read()
        
        # Validate file content
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file provided")
        
        client = get_gcs_client()
        bucket = client.bucket(DEFAULT_BUCKET)
        
        # Create blob with the original filename
        blob = bucket.blob(file.filename)
        
        blob.upload_from_string(content, content_type=file.content_type)
        
        return {
            "message": f"File '{file.filename}' uploaded successfully",
            "filename": file.filename,
            "size": len(content),
            "contentType": file.content_type
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

@router.delete("/bucket/{bucket_name}/file/{file_name}")
async def delete_file(bucket_name: str, file_name: str):
    """Delete a file from a bucket"""
    try:
        # Allow deletion from default bucket (uploaded files)
        if bucket_name == DEFAULT_BUCKET:
            client = get_gcs_client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(file_name)
            
            if not blob.exists():
                raise HTTPException(status_code=404, detail=f"File '{file_name}' not found")
            
            blob.delete()
            return {"message": f"File '{file_name}' deleted successfully"}
        else:
            # For other buckets, deletion is not supported as we have read-only access
            raise HTTPException(
                status_code=403, 
                detail="File deletion not supported for public buckets. Use authenticated access for write operations."
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")