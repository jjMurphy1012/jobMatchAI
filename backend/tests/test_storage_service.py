from pathlib import Path

import pytest

from app.services.storage_service import LocalStorageService


@pytest.mark.asyncio
async def test_local_storage_upload_and_delete(tmp_path: Path):
    service = LocalStorageService(root_dir=tmp_path)

    stored_file = await service.upload_resume("resume-1", "resume.pdf", b"hello pdf")

    file_path = Path(stored_file.path)
    assert stored_file.provider == "local"
    assert file_path.exists()
    assert file_path.read_bytes() == b"hello pdf"

    await service.delete_file(stored_file)

    assert not file_path.exists()
