import os
import uuid
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import boto3
from botocore.exceptions import BotoCoreError, ClientError


configured_bucket = os.getenv("S3_BUCKET", "").strip()
BUCKET_NAME = (
    None
    if configured_bucket.lower() in {"", "your_s3_bucket_name"}
    else configured_bucket
)
LOCAL_UPLOAD_DIR = Path(
    os.getenv(
        "LOCAL_UPLOAD_DIR",
        str(Path(__file__).resolve().parent.parent / "uploads")
    )
).resolve()

s3 = (
    boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION", "ap-south-1")
    )
    if BUCKET_NAME
    else None
)


class StorageError(RuntimeError):
    def __init__(self, message, code="StorageError"):
        super().__init__(message)
        self.code = code


def validate_storage_config():
    if BUCKET_NAME and s3 is None:
        raise StorageError("S3 client is unavailable", "MissingS3Client")


def check_storage():
    if not BUCKET_NAME:
        try:
            LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise StorageError("Local image storage is not writable", "LocalStorageError") from error
        return

    validate_storage_config()
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "ClientError")
        raise StorageError("S3 bucket check failed", code) from error
    except BotoCoreError as error:
        raise StorageError("AWS credentials or network check failed", "BotoCoreError") from error


def upload_image(
    file,
    folder="uploads"
):

    file.stream.seek(0)

    extension = os.path.splitext(
        file.filename
    )[1].lower()

    filename = (
        f"{uuid.uuid4()}{extension}"
    )

    folder_path = PurePosixPath(folder)
    if folder_path.is_absolute() or ".." in folder_path.parts:
        raise StorageError("Invalid image folder", "InvalidImagePath")

    key = str(folder_path / filename)

    if not BUCKET_NAME:
        destination = (LOCAL_UPLOAD_DIR / Path(*folder_path.parts) / filename).resolve()
        try:
            destination.relative_to(LOCAL_UPLOAD_DIR)
        except ValueError as error:
            raise StorageError("Invalid image path", "InvalidImagePath") from error

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            file.save(destination)
        except OSError as error:
            raise StorageError("Local image could not be saved", "LocalStorageError") from error
        return key

    validate_storage_config()
    try:
        s3.upload_fileobj(
            file,
            BUCKET_NAME,
            key,
            ExtraArgs={
                "ContentType": file.content_type or "application/octet-stream"
            }
        )
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "ClientError")
        raise StorageError("S3 rejected the image upload", code) from error
    except BotoCoreError as error:
        raise StorageError("AWS credentials or network upload failed", "BotoCoreError") from error

    return key


def generate_presigned_url(key):

    if not BUCKET_NAME:
        return f"/media/{quote(key, safe='/')}"

    validate_storage_config()
    return s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": BUCKET_NAME,
            "Key": key
        },
        ExpiresIn=3600
    )


def delete_image(key):

    if not BUCKET_NAME:
        target = (LOCAL_UPLOAD_DIR / key).resolve()
        try:
            target.relative_to(LOCAL_UPLOAD_DIR)
        except ValueError as error:
            raise StorageError("Invalid image path", "InvalidImagePath") from error
        target.unlink(missing_ok=True)
        return

    validate_storage_config()

    s3.delete_object(
        Bucket=BUCKET_NAME,
        Key=key
    )
