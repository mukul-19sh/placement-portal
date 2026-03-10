import os
import uuid
from typing import Optional
from pathlib import Path
from datetime import datetime
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

# Configuration
USE_CLOUD_STORAGE = os.getenv("USE_CLOUD_STORAGE", "false").lower() == "true"
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local")  # local, s3, cloudinary

# Local storage
LOCAL_STORAGE_PATH = Path("uploads")
LOCAL_STORAGE_PATH.mkdir(exist_ok=True)

# S3 Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

# File validation
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}


class StorageManager:
    """Manages file storage across different backends."""
    
    def __init__(self):
        self.storage_type = STORAGE_TYPE
        self._init_storage()
    
    def _init_storage(self):
        """Initialize the storage backend."""
        if self.storage_type == "s3" and USE_CLOUD_STORAGE:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                    region_name=AWS_REGION
                )
                # Test connection
                self.s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
                print("S3 storage initialized successfully")
            except (NoCredentialsError, ClientError) as e:
                print(f"S3 initialization failed: {e}")
                self.storage_type = "local"
        
        elif self.storage_type == "cloudinary" and USE_CLOUD_STORAGE:
            try:
                import cloudinary
                import cloudinary.uploader
                
                cloudinary.config(
                    cloud_name=CLOUDINARY_CLOUD_NAME,
                    api_key=CLOUDINARY_API_KEY,
                    api_secret=CLOUDINARY_API_SECRET
                )
                self.cloudinary = cloudinary
                print("Cloudinary storage initialized successfully")
            except ImportError:
                print("Cloudinary not installed, falling back to local storage")
                self.storage_type = "local"
            except Exception as e:
                print(f"Cloudinary initialization failed: {e}")
                self.storage_type = "local"
        
        else:
            print("Using local storage")
            self.storage_type = "local"
    
    def validate_file(self, file_content: bytes, filename: str) -> tuple[bool, str]:
        """Validate file size and type."""
        # Check file size
        if len(file_content) > MAX_FILE_SIZE:
            return False, f"File size exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit"
        
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            return False, f"File type {file_ext} not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        
        return True, "File is valid"
    
    def upload_file(self, file_content: bytes, filename: str, folder: str = "resumes") -> tuple[str, str]:
        """
        Upload file to storage.
        Returns: (file_url, storage_path)
        """
        # Validate file
        is_valid, message = self.validate_file(file_content, filename)
        if not is_valid:
            raise ValueError(message)
        
        # Generate unique filename
        file_ext = Path(filename).suffix.lower()
        unique_filename = f"{uuid.uuid4().hex}_{int(datetime.utcnow().timestamp())}{file_ext}"
        
        if self.storage_type == "s3":
            return self._upload_to_s3(file_content, unique_filename, folder)
        elif self.storage_type == "cloudinary":
            return self._upload_to_cloudinary(file_content, unique_filename, folder)
        else:
            return self._upload_to_local(file_content, unique_filename, folder)
    
    def _upload_to_local(self, file_content: bytes, filename: str, folder: str) -> tuple[str, str]:
        """Upload file to local storage."""
        folder_path = LOCAL_STORAGE_PATH / folder
        folder_path.mkdir(exist_ok=True)
        
        file_path = folder_path / filename
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Return relative URL for web access
        file_url = f"/{folder}/{filename}"
        return file_url, str(file_path)
    
    def _upload_to_s3(self, file_content: bytes, filename: str, folder: str) -> tuple[str, str]:
        """Upload file to S3."""
        key = f"{folder}/{filename}"
        
        try:
            self.s3_client.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=key,
                Body=file_content,
                ContentType=self._get_content_type(filename)
            )
            
            # Generate URL
            file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key}"
            return file_url, key
            
        except ClientError as e:
            raise Exception(f"S3 upload failed: {e}")
    
    def _upload_to_cloudinary(self, file_content: bytes, filename: str, folder: str) -> tuple[str, str]:
        """Upload file to Cloudinary."""
        try:
            # Upload to Cloudinary
            response = self.cloudinary.uploader.upload(
                file_content,
                public_id=f"{folder}/{filename}",
                resource_type="raw",  # For non-image files
                folder=folder
            )
            
            file_url = response.get('secure_url')
            storage_path = response.get('public_id')
            
            return file_url, storage_path
            
        except Exception as e:
            raise Exception(f"Cloudinary upload failed: {e}")
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from storage."""
        try:
            if self.storage_type == "s3" and file_path.startswith("https://"):
                # Extract S3 key from URL
                key = "/".join(file_path.split("/")[-2:])
                self.s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=key)
                
            elif self.storage_type == "cloudinary" and "/" in file_path:
                # Extract public_id from URL or path
                public_id = file_path.split("/")[-2] + "/" + file_path.split("/")[-1]
                self.cloudinary.uploader.destroy(public_id, resource_type="raw")
                
            else:
                # Local file deletion
                if file_path.startswith("/"):
                    full_path = Path(file_path)
                else:
                    full_path = LOCAL_STORAGE_PATH / file_path
                
                if full_path.exists():
                    full_path.unlink()
            
            return True
            
        except Exception as e:
            print(f"Failed to delete file {file_path}: {e}")
            return False
    
    def _get_content_type(self, filename: str) -> str:
        """Get MIME type based on file extension."""
        ext = Path(filename).suffix.lower()
        content_types = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }
        return content_types.get(ext, "application/octet-stream")


# Global storage manager instance
storage_manager = StorageManager()
