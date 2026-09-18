import os
import uuid
import boto3
from botocore.exceptions import BotoCoreError, ClientError


s3 = boto3.client(
    "s3",
    region_name=os.getenv(
        "AWS_REGION",
        "ap-south-1"
    )
)


BUCKET_NAME = os.getenv(
    "S3_BUCKET"
)


class StorageError(RuntimeError):
    def __init__(self, message, code="StorageError"):
        super().__init__(message)
        self.code = code


def validate_storage_config():
    if not BUCKET_NAME:
        raise StorageError("S3_BUCKET is not configured", "MissingBucket")


def check_storage():
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

    validate_storage_config()

    file.stream.seek(0)

    extension = os.path.splitext(
        file.filename
    )[1].lower()

    filename = (
        f"{uuid.uuid4()}{extension}"
    )

    key = (
        f"{folder}/{filename}"
    )

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

    validate_storage_config()

    s3.delete_object(
        Bucket=BUCKET_NAME,
        Key=key
    )
