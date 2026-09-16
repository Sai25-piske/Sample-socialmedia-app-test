import os
import uuid
import boto3


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


def upload_image(
    file,
    folder="uploads"
):

    extension = os.path.splitext(
        file.filename
    )[1].lower()

    filename = (
        f"{uuid.uuid4()}{extension}"
    )

    key = (
        f"{folder}/{filename}"
    )

    s3.upload_fileobj(
        file,
        BUCKET_NAME,
        key,
        ExtraArgs={
            "ContentType":
                file.content_type
        }
    )

    return key


def generate_presigned_url(key):

    return s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": BUCKET_NAME,
            "Key": key
        },
        ExpiresIn=3600
    )


def delete_image(key):

    s3.delete_object(
        Bucket=BUCKET_NAME,
        Key=key
    )
