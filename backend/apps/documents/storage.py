import boto3
from botocore.exceptions import ClientError
from django.conf import settings


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def upload_file(file_obj, storage_key: str) -> None:
    """Upload a file-like object to the configured bucket."""
    client = _s3_client()
    client.upload_fileobj(file_obj, settings.AWS_STORAGE_BUCKET_NAME, storage_key)


def delete_file(storage_key: str) -> None:
    """Delete an object from the bucket. Silently ignores any storage errors."""
    try:
        client = _s3_client()
        client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=storage_key)
    except Exception:
        pass


def generate_presigned_url(storage_key: str, expires_in: int = 300) -> str:
    """Return a pre-signed download URL valid for `expires_in` seconds."""
    client = _s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": storage_key},
        ExpiresIn=expires_in,
    )


def ensure_bucket_exists() -> None:
    """Create the bucket if it doesn't exist (useful on first startup)."""
    client = _s3_client()
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)
