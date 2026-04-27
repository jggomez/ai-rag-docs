from abc import ABC, abstractmethod

class StorageRepository(ABC):
    @abstractmethod
    def download_file(self, bucket_name: str, object_name: str) -> bytes:
        """Download a file from storage as bytes."""
        pass

    @abstractmethod
    def upload_file(self, bucket_name: str, object_name: str, content: bytes, content_type: str = None) -> str:
        """Upload content to storage and return the URL or path."""
        pass

from google.cloud import storage

class GCSStorageRepository(StorageRepository):
    def __init__(self, client: storage.Client = None):
        self.client = client or storage.Client()

    def download_file(self, bucket_name: str, object_name: str) -> bytes:
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        return blob.download_as_bytes()

    def upload_file(self, bucket_name: str, object_name: str, content: bytes, content_type: str = None) -> str:
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        blob.upload_from_string(content, content_type=content_type)
        return f"gs://{bucket_name}/{object_name}"
