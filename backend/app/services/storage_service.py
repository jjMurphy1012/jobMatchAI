from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import mimetypes

import httpx

from app.core.config import settings


class StorageServiceError(RuntimeError):
    pass


@dataclass
class StoredFile:
    provider: str
    path: str
    bucket: Optional[str] = None


class BaseStorageService:
    async def upload_resume(self, object_id: str, file_name: str, content: bytes) -> StoredFile:
        raise NotImplementedError

    async def delete_file(self, stored_file: StoredFile) -> None:
        raise NotImplementedError

    async def create_download_url(self, stored_file: StoredFile) -> Optional[str]:
        return None


class LocalStorageService(BaseStorageService):
    def __init__(self, root_dir: Optional[Path] = None):
        base_dir = root_dir or Path(settings.LOCAL_STORAGE_DIR)
        if not base_dir.is_absolute():
            base_dir = Path.cwd() / base_dir
        self.root_dir = base_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    async def upload_resume(self, object_id: str, file_name: str, content: bytes) -> StoredFile:
        suffix = Path(file_name).suffix or ".pdf"
        file_path = self.root_dir / f"{object_id}{suffix}"
        file_path.write_bytes(content)
        return StoredFile(provider="local", path=str(file_path))

    async def delete_file(self, stored_file: StoredFile) -> None:
        path = Path(stored_file.path)
        if path.exists():
            path.unlink()


class SupabaseStorageService(BaseStorageService):
    def __init__(self):
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise StorageServiceError("Supabase storage is not configured")

        self.base_url = settings.SUPABASE_URL.rstrip("/")
        self.bucket = settings.SUPABASE_RESUME_BUCKET
        self.api_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self._client = httpx.AsyncClient(timeout=30.0)

    def _headers(self, content_type: Optional[str] = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "apikey": self.api_key,
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    async def upload_resume(self, object_id: str, file_name: str, content: bytes) -> StoredFile:
        suffix = Path(file_name).suffix or ".pdf"
        object_path = f"resumes/{object_id}{suffix}"
        content_type = mimetypes.guess_type(file_name)[0] or "application/pdf"
        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{object_path}"

        response = await self._client.post(
            url,
            headers={**self._headers(content_type), "x-upsert": "true"},
            content=content,
        )
        response.raise_for_status()

        return StoredFile(provider="supabase", bucket=self.bucket, path=object_path)

    async def delete_file(self, stored_file: StoredFile) -> None:
        if not stored_file.bucket:
            return

        url = f"{self.base_url}/storage/v1/object/{stored_file.bucket}/{stored_file.path}"
        response = await self._client.delete(url, headers=self._headers())
        if response.status_code not in (200, 204, 404):
            response.raise_for_status()

    async def create_download_url(self, stored_file: StoredFile) -> Optional[str]:
        if not stored_file.bucket:
            return None

        url = f"{self.base_url}/storage/v1/object/sign/{stored_file.bucket}/{stored_file.path}"
        payload = {"expiresIn": settings.SUPABASE_SIGNED_URL_TTL_SECONDS}

        response = await self._client.post(url, headers=self._headers("application/json"), json=payload)
        response.raise_for_status()
        data = response.json()

        signed_url = data.get("signedURL")
        if not signed_url:
            return None

        if signed_url.startswith("http"):
            return signed_url

        return f"{self.base_url}/storage/v1{signed_url}"


def get_storage_service() -> BaseStorageService:
    if settings.STORAGE_BACKEND == "supabase":
        return SupabaseStorageService()

    return LocalStorageService()
