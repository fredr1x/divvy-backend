import mimetypes
import os
import uuid

from io import BytesIO
from typing import Optional

from minio import Minio
from starlette.responses import StreamingResponse


class MinioService:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool = False):
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        self.default_bucket = "groups"
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        if not self.client.bucket_exists(self.default_bucket):
            self.client.make_bucket(self.default_bucket)

    def get_file(
            self,
            key: str
    ):
        response = self.client.get_object(self.default_bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def get_file_stream(
            self,
            key: str
    ) -> StreamingResponse:
        response = self.client.get_object(self.default_bucket, key)
        stat = self.client.stat_object(self.default_bucket, key)

        def iterator():
            try:
                yield from response.stream(32 * 1024)
            finally:
                response.close()
                response.release_conn()

        return StreamingResponse(
            iterator(),
            media_type=stat.content_type or "application/octet-stream",
            headers={"Content-Disposition": f'inline; filename="{key.split("/")[-1]}"'},
        )

    def upload(
            self,
            file_data: bytes,
            object_key: str,
            content_type: Optional[str] = None,
            bucket: Optional[str] = None
    ) -> str:
        bucket = bucket or self.default_bucket

        if content_type is None:
            content_type = mimetypes.guess_type(object_key)[0] or 'application/octet-stream'

        file_stream = BytesIO(file_data)
        size = len(file_data)

        self.client.put_object(
            bucket_name=bucket,
            object_name=object_key,
            data=file_stream,
            length=size,
            content_type=content_type
        )

        url = self.get_url(object_key, bucket)

        return url

    def get_url(self, object_key: str, bucket: Optional[str] = None) -> str:
        bucket = bucket or self.default_bucket
        return self.client.presigned_get_object(bucket, object_key)

    def delete(self, object_key: str, bucket: Optional[str] = None):
        bucket = bucket or self.default_bucket
        self.client.remove_object(bucket, object_key)

    @staticmethod
    def generate_object_key(group_id: int, category: str, filename: str) -> str:
        return f"groups/{group_id}/{category}/{uuid.uuid4()}/{filename}"


minio_service = MinioService(
    endpoint=os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
)
