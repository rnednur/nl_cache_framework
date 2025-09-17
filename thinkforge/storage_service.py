"""
External storage service for handling cloud storage operations.
Supports S3, GCS, and Azure storage backends for ThinkForge spaces.
"""

import os
import json
import uuid
from typing import Optional, Dict, Any, BinaryIO, Union, Tuple
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import tempfile
import logging

from .hotcommands_models import StorageBackend

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class StorageBackendInterface(ABC):
    """Abstract interface for storage backends."""
    
    @abstractmethod
    def upload_file(self, file_path: str, content: Union[str, bytes, BinaryIO], 
                   content_type: str = None, metadata: Dict[str, Any] = None) -> str:
        """Upload file and return storage path."""
        pass
    
    @abstractmethod
    def download_file(self, storage_path: str) -> bytes:
        """Download file content."""
        pass
    
    @abstractmethod
    def get_public_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """Get public/pre-signed URL for file access."""
        pass
    
    @abstractmethod
    def delete_file(self, storage_path: str) -> bool:
        """Delete file from storage."""
        pass
    
    @abstractmethod
    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists."""
        pass


class LocalStorageBackend(StorageBackendInterface):
    """Local filesystem storage backend."""
    
    def __init__(self, base_path: str = "storage/spaces"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    def upload_file(self, file_path: str, content: Union[str, bytes, BinaryIO], 
                   content_type: str = None, metadata: Dict[str, Any] = None) -> str:
        """Upload file to local storage."""
        full_path = os.path.join(self.base_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        if hasattr(content, 'read'):
            content = content.read()
        
        with open(full_path, 'wb') as f:
            f.write(content)
        
        # Store metadata alongside file
        if metadata:
            metadata_path = f"{full_path}.metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
        
        return file_path
    
    def download_file(self, storage_path: str) -> bytes:
        """Download file from local storage."""
        full_path = os.path.join(self.base_path, storage_path)
        if not os.path.exists(full_path):
            raise StorageError(f"File not found: {storage_path}")
        
        with open(full_path, 'rb') as f:
            return f.read()
    
    def get_public_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """Get local file URL (for development/testing)."""
        return f"/api/v1/spaces/files/{storage_path}"
    
    def delete_file(self, storage_path: str) -> bool:
        """Delete file from local storage."""
        full_path = os.path.join(self.base_path, storage_path)
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
            
            # Remove metadata file if exists
            metadata_path = f"{full_path}.metadata.json"
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {storage_path}: {e}")
            return False
    
    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists in local storage."""
        full_path = os.path.join(self.base_path, storage_path)
        return os.path.exists(full_path)


class S3StorageBackend(StorageBackendInterface):
    """Amazon S3 storage backend."""
    
    def __init__(self, bucket_name: str, region: str = None, 
                 aws_access_key_id: str = None, aws_secret_access_key: str = None):
        self.bucket_name = bucket_name
        self.region = region
        
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            self.ClientError = ClientError
            
            # Initialize S3 client
            session_kwargs = {}
            if aws_access_key_id and aws_secret_access_key:
                session_kwargs.update({
                    'aws_access_key_id': aws_access_key_id,
                    'aws_secret_access_key': aws_secret_access_key
                })
            
            if region:
                session_kwargs['region_name'] = region
            
            self.s3_client = boto3.client('s3', **session_kwargs)
            
        except ImportError:
            raise StorageError("boto3 library is required for S3 storage backend")
    
    def upload_file(self, file_path: str, content: Union[str, bytes, BinaryIO], 
                   content_type: str = None, metadata: Dict[str, Any] = None) -> str:
        """Upload file to S3."""
        try:
            if isinstance(content, str):
                content = content.encode('utf-8')
            
            if hasattr(content, 'read'):
                # File-like object
                upload_kwargs = {'Fileobj': content}
            else:
                # Bytes content
                import io
                upload_kwargs = {'Fileobj': io.BytesIO(content)}
            
            upload_kwargs.update({
                'Bucket': self.bucket_name,
                'Key': file_path
            })
            
            if content_type:
                upload_kwargs['ExtraArgs'] = {'ContentType': content_type}
            
            if metadata:
                if 'ExtraArgs' not in upload_kwargs:
                    upload_kwargs['ExtraArgs'] = {}
                upload_kwargs['ExtraArgs']['Metadata'] = {
                    k: str(v) for k, v in metadata.items()
                }
            
            self.s3_client.upload_fileobj(**upload_kwargs)
            return file_path
            
        except self.ClientError as e:
            raise StorageError(f"Failed to upload to S3: {e}")
    
    def download_file(self, storage_path: str) -> bytes:
        """Download file from S3."""
        try:
            import io
            buffer = io.BytesIO()
            self.s3_client.download_fileobj(self.bucket_name, storage_path, buffer)
            return buffer.getvalue()
            
        except self.ClientError as e:
            raise StorageError(f"Failed to download from S3: {e}")
    
    def get_public_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """Get pre-signed URL for S3 object."""
        try:
            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': storage_path},
                ExpiresIn=expires_in
            )
        except self.ClientError as e:
            raise StorageError(f"Failed to generate S3 URL: {e}")
    
    def delete_file(self, storage_path: str) -> bool:
        """Delete file from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=storage_path)
            return True
        except self.ClientError as e:
            logger.error(f"Failed to delete S3 file {storage_path}: {e}")
            return False
    
    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=storage_path)
            return True
        except self.ClientError:
            return False


class GCSStorageBackend(StorageBackendInterface):
    """Google Cloud Storage backend."""
    
    def __init__(self, bucket_name: str, credentials_path: str = None):
        self.bucket_name = bucket_name
        
        try:
            from google.cloud import storage
            from google.cloud.exceptions import NotFound
            
            self.NotFound = NotFound
            
            # Initialize GCS client
            if credentials_path:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
            
            self.client = storage.Client()
            self.bucket = self.client.bucket(bucket_name)
            
        except ImportError:
            raise StorageError("google-cloud-storage library is required for GCS backend")
    
    def upload_file(self, file_path: str, content: Union[str, bytes, BinaryIO], 
                   content_type: str = None, metadata: Dict[str, Any] = None) -> str:
        """Upload file to GCS."""
        try:
            blob = self.bucket.blob(file_path)
            
            if content_type:
                blob.content_type = content_type
            
            if metadata:
                blob.metadata = {k: str(v) for k, v in metadata.items()}
            
            if isinstance(content, str):
                blob.upload_from_string(content)
            elif hasattr(content, 'read'):
                blob.upload_from_file(content)
            else:
                blob.upload_from_string(content)
            
            return file_path
            
        except Exception as e:
            raise StorageError(f"Failed to upload to GCS: {e}")
    
    def download_file(self, storage_path: str) -> bytes:
        """Download file from GCS."""
        try:
            blob = self.bucket.blob(storage_path)
            return blob.download_as_bytes()
            
        except self.NotFound:
            raise StorageError(f"File not found in GCS: {storage_path}")
        except Exception as e:
            raise StorageError(f"Failed to download from GCS: {e}")
    
    def get_public_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """Get signed URL for GCS object."""
        try:
            blob = self.bucket.blob(storage_path)
            expiration = datetime.utcnow() + timedelta(seconds=expires_in)
            return blob.generate_signed_url(expiration=expiration)
            
        except Exception as e:
            raise StorageError(f"Failed to generate GCS URL: {e}")
    
    def delete_file(self, storage_path: str) -> bool:
        """Delete file from GCS."""
        try:
            blob = self.bucket.blob(storage_path)
            blob.delete()
            return True
        except Exception as e:
            logger.error(f"Failed to delete GCS file {storage_path}: {e}")
            return False
    
    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists in GCS."""
        try:
            blob = self.bucket.blob(storage_path)
            return blob.exists()
        except:
            return False


class ThinkForgeStorageService:
    """Main storage service that manages different storage backends for ThinkForge."""
    
    def __init__(self):
        self.backends: Dict[StorageBackend, StorageBackendInterface] = {}
        self._setup_backends()
    
    def _setup_backends(self):
        """Initialize storage backends based on configuration."""
        # Local storage (always available)
        local_path = os.getenv('LOCAL_STORAGE_PATH', 'storage/spaces')
        self.backends[StorageBackend.LOCAL] = LocalStorageBackend(local_path)
        
        # S3 storage (if configured)
        s3_bucket = os.getenv('S3_BUCKET_NAME')
        if s3_bucket:
            try:
                self.backends[StorageBackend.S3] = S3StorageBackend(
                    bucket_name=s3_bucket,
                    region=os.getenv('S3_REGION'),
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                )
                logger.info("S3 storage backend initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize S3 backend: {e}")
        
        # GCS storage (if configured)
        gcs_bucket = os.getenv('GCS_BUCKET_NAME')
        if gcs_bucket:
            try:
                self.backends[StorageBackend.GCS] = GCSStorageBackend(
                    bucket_name=gcs_bucket,
                    credentials_path=os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                )
                logger.info("GCS storage backend initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize GCS backend: {e}")
    
    def get_backend(self, backend_type: StorageBackend) -> StorageBackendInterface:
        """Get storage backend instance."""
        if backend_type not in self.backends:
            raise StorageError(f"Storage backend {backend_type} not available")
        return self.backends[backend_type]
    
    def upload_space_content(self, space_id: int, content: Union[str, bytes], 
                           backend: StorageBackend = StorageBackend.LOCAL,
                           content_type: str = None) -> Tuple[str, str]:
        """Upload space content and return storage path and public URL."""
        backend_instance = self.get_backend(backend)
        
        # Generate unique file path
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        file_ext = self._get_file_extension(content_type)
        file_path = f"spaces/{space_id}/{timestamp}_{uuid.uuid4().hex[:8]}{file_ext}"
        
        metadata = {
            'space_id': space_id,
            'upload_time': datetime.utcnow().isoformat(),
            'content_type': content_type or 'application/octet-stream'
        }
        
        try:
            storage_path = backend_instance.upload_file(
                file_path, content, content_type, metadata
            )
            public_url = backend_instance.get_public_url(storage_path)
            
            return storage_path, public_url
            
        except Exception as e:
            logger.error(f"Failed to upload space content: {e}")
            raise StorageError(f"Upload failed: {e}")
    
    def upload_webpage_export(self, space_id: int, html_content: str,
                            backend: StorageBackend = StorageBackend.LOCAL) -> Tuple[str, str]:
        """Upload webpage export for sharing."""
        return self.upload_space_content(
            space_id, html_content, backend, 'text/html'
        )
    
    def download_space_content(self, storage_path: str, 
                             backend: StorageBackend = StorageBackend.LOCAL) -> bytes:
        """Download space content."""
        backend_instance = self.get_backend(backend)
        return backend_instance.download_file(storage_path)
    
    def get_public_url(self, storage_path: str, 
                      backend: StorageBackend = StorageBackend.LOCAL,
                      expires_in: int = 3600) -> str:
        """Get public URL for space content."""
        backend_instance = self.get_backend(backend)
        return backend_instance.get_public_url(storage_path, expires_in)
    
    def delete_space_content(self, storage_path: str,
                           backend: StorageBackend = StorageBackend.LOCAL) -> bool:
        """Delete space content."""
        backend_instance = self.get_backend(backend)
        return backend_instance.delete_file(storage_path)
    
    def generate_html_report(self, space_data: Dict[str, Any], 
                           execution_result: Dict[str, Any] = None) -> str:
        """Generate HTML report from space data."""
        title = space_data.get('display_name') or space_data.get('name', 'Space Report')
        description = space_data.get('description', 'ThinkForge Space Report')
        
        # Extract result data if available
        result_data = execution_result.get('result_data', {}) if execution_result else space_data.get('content_data', {})
        rows = result_data.get('rows', [])
        columns = result_data.get('columns', [])
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f8fafc;
                    color: #1e293b;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 2rem;
                    font-weight: 600;
                }}
                .header p {{
                    margin: 10px 0 0 0;
                    opacity: 0.9;
                }}
                .metadata {{
                    background: #f1f5f9;
                    padding: 20px 30px;
                    border-bottom: 1px solid #e2e8f0;
                }}
                .metadata-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                }}
                .metadata-item {{
                    background: white;
                    padding: 15px;
                    border-radius: 8px;
                    border: 1px solid #e2e8f0;
                }}
                .metadata-label {{
                    font-size: 0.875rem;
                    font-weight: 600;
                    color: #64748b;
                    margin-bottom: 5px;
                }}
                .metadata-value {{
                    font-size: 1rem;
                    color: #1e293b;
                }}
                .content {{
                    padding: 30px;
                }}
                .table-container {{
                    overflow-x: auto;
                    border-radius: 8px;
                    border: 1px solid #e2e8f0;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 0.875rem;
                }}
                th {{
                    background-color: #f8fafc;
                    padding: 12px 16px;
                    text-align: left;
                    font-weight: 600;
                    color: #374151;
                    border-bottom: 2px solid #e5e7eb;
                }}
                td {{
                    padding: 12px 16px;
                    border-bottom: 1px solid #f3f4f6;
                }}
                tr:hover {{
                    background-color: #f9fafb;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e2e8f0;
                    font-size: 0.875rem;
                    color: #64748b;
                    text-align: center;
                }}
                .tag {{
                    display: inline-block;
                    background: #dbeafe;
                    color: #1e40af;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 0.75rem;
                    margin-right: 8px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{title}</h1>
                    <p>{description}</p>
                </div>
                
                <div class="metadata">
                    <div class="metadata-grid">
                        <div class="metadata-item">
                            <div class="metadata-label">Space ID</div>
                            <div class="metadata-value">{space_data.get('id', 'N/A')}</div>
                        </div>
                        <div class="metadata-item">
                            <div class="metadata-label">Content Type</div>
                            <div class="metadata-value">{space_data.get('content_type', 'N/A').replace('_', ' ').title()}</div>
                        </div>
                        <div class="metadata-item">
                            <div class="metadata-label">Domain</div>
                            <div class="metadata-value">{space_data.get('domain', 'N/A')}</div>
                        </div>
                        <div class="metadata-item">
                            <div class="metadata-label">Generated</div>
                            <div class="metadata-value">{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</div>
                        </div>
                    </div>
                </div>
                
                <div class="content">
                    <h2>Data Results</h2>
        """
        
        if rows and columns:
            html += """
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
            """
            
            # Add column headers
            for column in columns:
                html += f"<th>{column}</th>"
            
            html += """
                                </tr>
                            </thead>
                            <tbody>
            """
            
            # Add data rows
            for row in rows:
                html += "<tr>"
                for cell in row:
                    html += f"<td>{cell}</td>"
                html += "</tr>"
            
            html += """
                            </tbody>
                        </table>
                    </div>
            """
        else:
            html += """
                    <div style="text-align: center; padding: 40px; color: #64748b;">
                        <p>No data available to display</p>
                    </div>
            """
        
        html += f"""
                </div>
                
                <div class="footer">
                    <p>Generated by ThinkForge • Space #{space_data.get('id', 'N/A')} • {datetime.utcnow().strftime('%B %d, %Y')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _get_file_extension(self, content_type: str) -> str:
        """Get appropriate file extension based on content type."""
        extensions = {
            'application/json': '.json',
            'text/html': '.html',
            'text/csv': '.csv',
            'application/pdf': '.pdf',
            'image/png': '.png',
            'image/jpeg': '.jpg',
            'text/plain': '.txt'
        }
        return extensions.get(content_type, '.dat')


# Global storage service instance
storage_service = ThinkForgeStorageService()