"""Cloud storage plugins for DocTagger.

This module provides storage plugins for cloud providers:
- S3 (AWS, MinIO, etc.)
- Google Cloud Storage
- Azure Blob Storage

Usage:
    ```python
    from doctagger.storage import S3Storage, register_storage

    s3 = S3Storage(
        bucket="my-bucket",
        access_key="...",
        secret_key="...",
    )
    register_storage(s3)
    ```
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .plugins import StoragePlugin, register_plugin

logger = logging.getLogger(__name__)


class LocalStorage(StoragePlugin):
    """Local filesystem storage (default)."""

    name = "local"
    version = "1.0.0"
    description = "Local filesystem storage"

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize local storage.

        Args:
            base_path: Base directory for storage
        """
        super().__init__()
        self.base_path = base_path or Path.cwd()

    def save(self, file_path: Path, destination: str, metadata: Dict[str, Any]) -> str:
        """Save file to local storage."""
        dest_path = self.base_path / destination
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        import shutil
        shutil.copy2(file_path, dest_path)

        return str(dest_path)

    def load(self, source: str, local_path: Path) -> Path:
        """Load file from local storage."""
        source_path = Path(source)
        if source_path.is_absolute():
            import shutil
            shutil.copy2(source_path, local_path)
        else:
            import shutil
            shutil.copy2(self.base_path / source, local_path)
        return local_path

    def delete(self, path: str) -> bool:
        """Delete file from local storage."""
        try:
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = self.base_path / path
            file_path.unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")
            return False

    def list(self, prefix: str = "") -> List[str]:
        """List files in local storage."""
        search_path = self.base_path / prefix if prefix else self.base_path
        if not search_path.exists():
            return []
        return [str(p.relative_to(self.base_path)) for p in search_path.rglob("*") if p.is_file()]


class S3Storage(StoragePlugin):
    """AWS S3 compatible storage (S3, MinIO, DigitalOcean Spaces, etc.)."""

    name = "s3"
    version = "1.0.0"
    description = "AWS S3 compatible storage"

    def __init__(
        self,
        bucket: str,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        region: str = "us-east-1",
    ):
        """
        Initialize S3 storage.

        Args:
            bucket: S3 bucket name
            access_key: AWS access key (or use env AWS_ACCESS_KEY_ID)
            secret_key: AWS secret key (or use env AWS_SECRET_ACCESS_KEY)
            endpoint_url: Custom endpoint URL (for MinIO, etc.)
            region: AWS region
        """
        super().__init__()
        self.bucket = bucket
        self.access_key = access_key or os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = secret_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.endpoint_url = endpoint_url
        self.region = region
        self._client = None

    @property
    def client(self):
        """Lazy-load boto3 client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "s3",
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    endpoint_url=self.endpoint_url,
                    region_name=self.region,
                )
            except ImportError:
                raise ImportError("boto3 is required for S3 storage. Install with: pip install boto3")
        return self._client

    def save(self, file_path: Path, destination: str, metadata: Dict[str, Any]) -> str:
        """Upload file to S3."""
        try:
            extra_args = {}
            if metadata:
                extra_args["Metadata"] = {k: str(v) for k, v in metadata.items() if v is not None}

            self.client.upload_file(
                str(file_path),
                self.bucket,
                destination,
                ExtraArgs=extra_args if extra_args else None,
            )

            return f"s3://{self.bucket}/{destination}"

        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise

    def load(self, source: str, local_path: Path) -> Path:
        """Download file from S3."""
        try:
            # Handle s3:// URLs
            if source.startswith("s3://"):
                parts = source[5:].split("/", 1)
                bucket = parts[0]
                key = parts[1] if len(parts) > 1 else ""
            else:
                bucket = self.bucket
                key = source

            local_path.parent.mkdir(parents=True, exist_ok=True)
            self.client.download_file(bucket, key, str(local_path))

            return local_path

        except Exception as e:
            logger.error(f"Failed to download from S3: {e}")
            raise

    def delete(self, path: str) -> bool:
        """Delete file from S3."""
        try:
            if path.startswith("s3://"):
                parts = path[5:].split("/", 1)
                key = parts[1] if len(parts) > 1 else ""
            else:
                key = path

            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True

        except Exception as e:
            logger.error(f"Failed to delete from S3: {e}")
            return False

    def list(self, prefix: str = "") -> List[str]:
        """List files in S3 bucket."""
        try:
            response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            return [obj["Key"] for obj in response.get("Contents", [])]
        except Exception as e:
            logger.error(f"Failed to list S3 objects: {e}")
            return []


class GCSStorage(StoragePlugin):
    """Google Cloud Storage."""

    name = "gcs"
    version = "1.0.0"
    description = "Google Cloud Storage"

    def __init__(
        self,
        bucket: str,
        credentials_file: Optional[str] = None,
        project: Optional[str] = None,
    ):
        """
        Initialize GCS storage.

        Args:
            bucket: GCS bucket name
            credentials_file: Path to service account JSON (or use GOOGLE_APPLICATION_CREDENTIALS)
            project: GCP project ID
        """
        super().__init__()
        self.bucket_name = bucket
        self.credentials_file = credentials_file or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.project = project
        self._client = None
        self._bucket = None

    @property
    def client(self):
        """Lazy-load GCS client."""
        if self._client is None:
            try:
                from google.cloud import storage
                if self.credentials_file:
                    self._client = storage.Client.from_service_account_json(
                        self.credentials_file, project=self.project
                    )
                else:
                    self._client = storage.Client(project=self.project)
            except ImportError:
                raise ImportError(
                    "google-cloud-storage is required. Install with: pip install google-cloud-storage"
                )
        return self._client

    @property
    def bucket(self):
        """Get bucket reference."""
        if self._bucket is None:
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket

    def save(self, file_path: Path, destination: str, metadata: Dict[str, Any]) -> str:
        """Upload file to GCS."""
        try:
            blob = self.bucket.blob(destination)
            if metadata:
                blob.metadata = {k: str(v) for k, v in metadata.items() if v is not None}
            blob.upload_from_filename(str(file_path))
            return f"gs://{self.bucket_name}/{destination}"
        except Exception as e:
            logger.error(f"Failed to upload to GCS: {e}")
            raise

    def load(self, source: str, local_path: Path) -> Path:
        """Download file from GCS."""
        try:
            if source.startswith("gs://"):
                parts = source[5:].split("/", 1)
                key = parts[1] if len(parts) > 1 else ""
            else:
                key = source

            local_path.parent.mkdir(parents=True, exist_ok=True)
            blob = self.bucket.blob(key)
            blob.download_to_filename(str(local_path))
            return local_path
        except Exception as e:
            logger.error(f"Failed to download from GCS: {e}")
            raise

    def delete(self, path: str) -> bool:
        """Delete file from GCS."""
        try:
            if path.startswith("gs://"):
                parts = path[5:].split("/", 1)
                key = parts[1] if len(parts) > 1 else ""
            else:
                key = path

            blob = self.bucket.blob(key)
            blob.delete()
            return True
        except Exception as e:
            logger.error(f"Failed to delete from GCS: {e}")
            return False

    def list(self, prefix: str = "") -> List[str]:
        """List files in GCS bucket."""
        try:
            blobs = self.client.list_blobs(self.bucket_name, prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"Failed to list GCS objects: {e}")
            return []


class AzureBlobStorage(StoragePlugin):
    """Azure Blob Storage."""

    name = "azure"
    version = "1.0.0"
    description = "Azure Blob Storage"

    def __init__(
        self,
        container: str,
        connection_string: Optional[str] = None,
        account_url: Optional[str] = None,
    ):
        """
        Initialize Azure Blob storage.

        Args:
            container: Container name
            connection_string: Azure connection string (or use AZURE_STORAGE_CONNECTION_STRING)
            account_url: Account URL (alternative to connection string)
        """
        super().__init__()
        self.container_name = container
        self.connection_string = connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.account_url = account_url
        self._client = None

    @property
    def client(self):
        """Lazy-load Azure client."""
        if self._client is None:
            try:
                from azure.storage.blob import BlobServiceClient
                if self.connection_string:
                    service_client = BlobServiceClient.from_connection_string(self.connection_string)
                else:
                    from azure.identity import DefaultAzureCredential
                    service_client = BlobServiceClient(
                        account_url=self.account_url,
                        credential=DefaultAzureCredential(),
                    )
                self._client = service_client.get_container_client(self.container_name)
            except ImportError:
                raise ImportError(
                    "azure-storage-blob is required. Install with: pip install azure-storage-blob"
                )
        return self._client

    def save(self, file_path: Path, destination: str, metadata: Dict[str, Any]) -> str:
        """Upload file to Azure Blob."""
        try:
            blob_client = self.client.get_blob_client(destination)
            with open(file_path, "rb") as f:
                blob_client.upload_blob(
                    f,
                    overwrite=True,
                    metadata={k: str(v) for k, v in metadata.items() if v is not None} if metadata else None,
                )
            return f"https://{self.client.account_name}.blob.core.windows.net/{self.container_name}/{destination}"
        except Exception as e:
            logger.error(f"Failed to upload to Azure: {e}")
            raise

    def load(self, source: str, local_path: Path) -> Path:
        """Download file from Azure Blob."""
        try:
            # Extract blob name from URL if needed
            if "blob.core.windows.net" in source:
                parts = source.split(f"{self.container_name}/", 1)
                key = parts[1] if len(parts) > 1 else source
            else:
                key = source

            local_path.parent.mkdir(parents=True, exist_ok=True)
            blob_client = self.client.get_blob_client(key)
            with open(local_path, "wb") as f:
                f.write(blob_client.download_blob().readall())
            return local_path
        except Exception as e:
            logger.error(f"Failed to download from Azure: {e}")
            raise

    def delete(self, path: str) -> bool:
        """Delete file from Azure Blob."""
        try:
            if "blob.core.windows.net" in path:
                parts = path.split(f"{self.container_name}/", 1)
                key = parts[1] if len(parts) > 1 else path
            else:
                key = path

            blob_client = self.client.get_blob_client(key)
            blob_client.delete_blob()
            return True
        except Exception as e:
            logger.error(f"Failed to delete from Azure: {e}")
            return False

    def list(self, prefix: str = "") -> List[str]:
        """List files in Azure container."""
        try:
            blobs = self.client.list_blobs(name_starts_with=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"Failed to list Azure blobs: {e}")
            return []


def register_storage(plugin: StoragePlugin) -> None:
    """Register a storage plugin."""
    register_plugin(plugin)
