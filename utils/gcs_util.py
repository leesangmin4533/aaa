from google.cloud import storage
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def download_from_gcs(bucket_name: str, source_blob_name: str, destination_file_path: Path):
    """Downloads a file from the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)

    try:
        destination_file_path.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(destination_file_path)
        logger.info(f"Blob {source_blob_name} downloaded to {destination_file_path}.")
    except Exception as e:
        logger.error(f"Failed to download {source_blob_name}: {e}", exc_info=True)

def upload_to_gcs(bucket_name: str, source_file_path: Path, destination_blob_name: str):
    """Uploads a file to the bucket."""
    if not source_file_path.exists():
        logger.warning(f"Source file {source_file_path} not found. Skipping upload.")
        return

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    try:
        blob.upload_from_filename(str(source_file_path))
        logger.info(f"File {source_file_path} uploaded to {destination_blob_name}.")
    except Exception as e:
        logger.error(f"Failed to upload {source_file_path}: {e}", exc_info=True)
