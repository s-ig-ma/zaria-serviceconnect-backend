from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.core.config import settings


def save_upload(upload: UploadFile, subfolder: str, prefix: str) -> str:
    content = upload.file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File must be smaller than 5 MB.")

    ext = Path(upload.filename or "").suffix or ".bin"
    relative_dir = Path("uploads") / subfolder
    relative_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{prefix}_{uuid4().hex}{ext}"
    absolute_path = relative_dir / filename

    with open(absolute_path, "wb") as file_obj:
        file_obj.write(content)

    return "/" + absolute_path.as_posix()
