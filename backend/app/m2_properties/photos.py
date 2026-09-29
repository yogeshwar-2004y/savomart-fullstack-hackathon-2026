import hashlib
import io
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

ALLOWED_FORMATS = {"JPEG": ("image/jpeg", ".jpg"), "PNG": ("image/png", ".png"), "WEBP": ("image/webp", ".webp")}
MAX_IMAGE_PIXELS = 40_000_000


class InvalidPhoto(ValueError):
    pass


@dataclass(frozen=True)
class StoredPhoto:
    storage_key: str
    original_filename: str
    content_type: str
    byte_size: int
    sha256: str


def inspect_photo(content: bytes, declared_type: str | None, max_bytes: int) -> tuple[str, str]:
    if not content:
        raise InvalidPhoto("Photo is empty")
    if len(content) > max_bytes:
        raise InvalidPhoto(f"Photo exceeds the {max_bytes // (1024 * 1024)} MB limit")
    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise InvalidPhoto("Image dimensions exceed the 40 megapixel limit")
            image.verify()
            detected = ALLOWED_FORMATS.get(image.format or "")
    except InvalidPhoto:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError) as exc:
        raise InvalidPhoto("File content is not a valid JPEG, PNG, or WebP image") from exc
    if not detected:
        raise InvalidPhoto("Only JPEG, PNG, and WebP images are allowed")
    content_type, extension = detected
    if declared_type and declared_type not in {content_type, "application/octet-stream"}:
        raise InvalidPhoto("Declared image type does not match the file content")
    return content_type, extension


def store_upload(upload: UploadFile, storage_path: str, max_bytes: int) -> StoredPhoto:
    content = upload.file.read(max_bytes + 1)
    content_type, extension = inspect_photo(content, upload.content_type, max_bytes)
    key = f"{uuid.uuid4().hex}{extension}"
    destination = Path(storage_path)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / key).write_bytes(content)
    return StoredPhoto(
        storage_key=key, original_filename=(upload.filename or "property-photo")[:240],
        content_type=content_type, byte_size=len(content), sha256=hashlib.sha256(content).hexdigest(),
    )
