import hashlib
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Dict, Optional, Tuple

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config.settings import settings


@dataclass(frozen=True)
class StoredObject:
    key: str
    bucket: str
    size: int
    sha256_hash: str
    etag: Optional[str] = None
    version_id: Optional[str] = None


class StorageService:
    def __init__(self):
        self.provider = settings.STORAGE_PROVIDER.lower()
        if self.provider not in {"minio", "s3"}:
            raise ValueError("STORAGE_PROVIDER must be 'minio' or 's3'.")

    @asynccontextmanager
    async def _client(self, endpoint_url: Optional[str] = None) -> AsyncIterator[object]:
        session = aioboto3.Session()
        client_kwargs = {
            "aws_access_key_id": settings.STORAGE_ACCESS_KEY,
            "aws_secret_access_key": settings.STORAGE_SECRET_KEY,
            "region_name": settings.STORAGE_REGION,
            "use_ssl": settings.STORAGE_SECURE,
            "config": Config(s3={"addressing_style": settings.STORAGE_ADDRESSING_STYLE}),
        }
        endpoint = endpoint_url if endpoint_url is not None else settings.STORAGE_ENDPOINT
        if endpoint:
            client_kwargs["endpoint_url"] = endpoint
        async with session.client(
            "s3",
            **client_kwargs,
        ) as client:
            yield client

    async def _ensure_bucket(self, client: object, bucket: str) -> None:
        try:
            await client.head_bucket(Bucket=bucket)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if not settings.STORAGE_CREATE_BUCKET or error_code not in {"404", "NoSuchBucket", "NotFound"}:
                raise
            await client.create_bucket(Bucket=bucket)

    @staticmethod
    def _put_options(metadata: Optional[Dict[str, str]] = None, content_type: Optional[str] = None) -> Dict[str, object]:
        options: Dict[str, object] = {"Metadata": metadata or {}}
        if content_type:
            options["ContentType"] = content_type
        if settings.STORAGE_SSE:
            options["ServerSideEncryption"] = settings.STORAGE_SSE
        if settings.STORAGE_SSE == "aws:kms" and settings.STORAGE_KMS_KEY_ID:
            options["SSEKMSKeyId"] = settings.STORAGE_KMS_KEY_ID
        return options

    async def check_health(self) -> bool:
        async with self._client() as client:
            try:
                await self._ensure_bucket(client, settings.STORAGE_BUCKET)
                await self._ensure_bucket(client, settings.STORAGE_BACKUP_BUCKET)
                return True
            except Exception:
                return False

    @staticmethod
    def _backup_key(key: str) -> str:
        return key

    async def save_file(
        self,
        content: bytes,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Tuple[str, int, str]:
        """Saves file bytes and returns (storage_key, file_size, sha256_hash)"""
        sha256_hash = hashlib.sha256(content).hexdigest()
        file_size = len(content)
        object_metadata = {"sha256": sha256_hash, **(metadata or {})}
        put_options = self._put_options(object_metadata, content_type)

        async with self._client() as client:
            await self._ensure_bucket(client, settings.STORAGE_BUCKET)
            await self._ensure_bucket(client, settings.STORAGE_BACKUP_BUCKET)
            await client.put_object(
                Bucket=settings.STORAGE_BUCKET,
                Key=key,
                Body=content,
                **put_options,
            )
            await client.put_object(
                Bucket=settings.STORAGE_BACKUP_BUCKET,
                Key=self._backup_key(key),
                Body=content,
                **self._put_options({**object_metadata, "canonical": "true"}, content_type),
            )

        return key, file_size, sha256_hash

    async def delete_file(self, key: str) -> None:
        async with self._client() as client:
            await client.delete_object(Bucket=settings.STORAGE_BUCKET, Key=key)
            await client.delete_object(Bucket=settings.STORAGE_BACKUP_BUCKET, Key=self._backup_key(key))

    async def create_download_url(self, key: str, file_name: str, content_type: str) -> str:
        endpoint = settings.STORAGE_PUBLIC_ENDPOINT or settings.STORAGE_ENDPOINT
        async with self._client(endpoint_url=endpoint) as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.STORAGE_BUCKET,
                    "Key": key,
                    "ResponseContentType": content_type,
                    "ResponseContentDisposition": f'attachment; filename="{file_name}"',
                },
                ExpiresIn=settings.STORAGE_PRESIGNED_URL_TTL,
            )

    async def read_file(self, key: str) -> Optional[bytes]:
        """Reads file bytes from storage"""
        async with self._client() as client:
            try:
                response = await client.get_object(Bucket=settings.STORAGE_BUCKET, Key=key)
            except ClientError as exc:
                if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                    return None
                raise
            async with response["Body"] as body:
                return await body.read()

    async def simulate_tamper(self, key: str, tamper_note: str = "Simulated bit flip/payload alteration") -> str:
        """Modifies bytes at storage level to demonstrate cryptographic mismatch per PRD Section 21"""
        original = await self.read_file(key)
        if original is None:
            raise FileNotFoundError(f"Object at {key} not found.")

        tampered_content = original + b"\n[TAMPERED_IN_TRANSIT: ALTERED_BYTES]"
        async with self._client() as client:
            await client.put_object(
                Bucket=settings.STORAGE_BUCKET,
                Key=key,
                Body=tampered_content,
            )

        return hashlib.sha256(tampered_content).hexdigest()

    async def restore_tamper(self, key: str) -> str:
        """Restores the canonical bytes from secure backup"""
        async with self._client() as client:
            try:
                response = await client.get_object(
                    Bucket=settings.STORAGE_BACKUP_BUCKET,
                    Key=self._backup_key(key),
                )
            except ClientError as exc:
                if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                    raise FileNotFoundError(f"Canonical backup for {key} not found.") from exc
                raise
            async with response["Body"] as body:
                canonical = await body.read()

        async with self._client() as client:
            await client.put_object(
                Bucket=settings.STORAGE_BUCKET,
                Key=key,
                Body=canonical,
                **self._put_options({"sha256": hashlib.sha256(canonical).hexdigest()}),
            )

        return hashlib.sha256(canonical).hexdigest()


storage_service = StorageService()
