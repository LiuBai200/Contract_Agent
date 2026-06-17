import re
import time
from pathlib import Path

from fastapi import UploadFile

from backend.schemas import UploadResponse


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md"}


def _safe_filename(filename: str) -> str:
    name = Path(filename or "uploaded_file").name
    name = re.sub(r"[^\w.\-\u4e00-\u9fff]", "_", name)
    return name or "uploaded_file"


async def save_upload_file(file: UploadFile, upload_dir: Path) -> UploadResponse:
    original_name = _safe_filename(file.filename)
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValueError(f"unsupported file type: {suffix or 'unknown'}, allowed: {allowed}")

    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_name = f"{int(time.time())}_{original_name}"
    saved_path = upload_dir / saved_name

    size = 0
    with saved_path.open("wb") as target:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            target.write(chunk)

    return UploadResponse(
        filename=original_name,
        saved_path=str(saved_path),
        size=size,
        content_type=file.content_type,
        message="File saved.",
    )
