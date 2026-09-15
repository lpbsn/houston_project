from __future__ import annotations

import io
from dataclasses import dataclass

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

from houston.uploads.validators import InvalidImageContentError

try:
    from PIL import ImageCms
except ImportError:  # pragma: no cover
    ImageCms = None

try:
    import pillow_heif
except ImportError:  # pragma: no cover
    pillow_heif = None

_JPEG_CONTENT_TYPE = "image/jpeg"
_JPEG_EXTENSION = "jpg"
_PNG_CONTENT_TYPE = "image/png"
_PNG_EXTENSION = "png"
_ALPHA_MODES = {"RGBA", "LA", "PA"}


@dataclass(frozen=True)
class NormalizedObservationPhoto:
    content_file: ContentFile
    content_type: str
    stored_extension: str
    size_bytes: int


def _ensure_heif_opener_registered() -> None:
    if pillow_heif is not None:
        pillow_heif.register_heif_opener()


def _has_useful_alpha(image: Image.Image) -> bool:
    if image.mode == "P" and "transparency" in image.info:
        alpha = image.convert("RGBA").getchannel("A")
        return alpha.getextrema()[0] < 255
    if image.mode not in _ALPHA_MODES:
        return False
    try:
        extrema = image.getchannel("A").getextrema()
    except ValueError:
        return False
    return extrema[0] < 255


def _working_image_and_target_mode(image: Image.Image) -> tuple[Image.Image, str]:
    target_mode = "RGBA" if _has_useful_alpha(image) else "RGB"
    icc_profile = image.info.get("icc_profile")
    if image.mode != target_mode:
        converted = image.convert(target_mode)
        if icc_profile and not converted.info.get("icc_profile"):
            converted.info["icc_profile"] = icc_profile
        image = converted
    return image, target_mode


def _convert_to_srgb_if_profile_usable(image: Image.Image, *, target_mode: str) -> Image.Image:
    icc_bytes = image.info.get("icc_profile")
    if not icc_bytes or ImageCms is None:
        return image
    try:
        source_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_bytes))
        destination_profile = ImageCms.createProfile("sRGB")
        converted = ImageCms.profileToProfile(
            image,
            source_profile,
            destination_profile,
            outputMode=target_mode,
        )
    except Exception:
        return image
    converted.info.pop("icc_profile", None)
    return converted


def _resize_without_upscale(image: Image.Image) -> Image.Image:
    max_edge = int(settings.HOUSTON_OBSERVATION_PHOTO_MAX_EDGE_PX)
    image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    return image


def _flatten_alpha_to_white(image: Image.Image) -> Image.Image:
    if image.mode == "RGB":
        return image
    if image.mode != "RGBA":
        return image.convert("RGB")
    background = Image.new("RGB", image.size, (255, 255, 255))
    background.paste(image, mask=image.getchannel("A"))
    return background


def _encode_thumbnail(image: Image.Image) -> NormalizedObservationPhoto:
    working = image.copy()
    max_edge = int(settings.HOUSTON_OBSERVATION_PHOTO_THUMB_EDGE_PX)
    working.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    working = _flatten_alpha_to_white(working)
    working.info.pop("icc_profile", None)
    working.info.pop("exif", None)
    buffer = io.BytesIO()
    working.save(
        buffer,
        format="JPEG",
        quality=int(settings.HOUSTON_OBSERVATION_PHOTO_THUMB_JPEG_QUALITY),
        optimize=True,
    )
    payload = buffer.getvalue()
    return NormalizedObservationPhoto(
        content_file=ContentFile(payload, name="photo.thumb.jpg"),
        content_type=_JPEG_CONTENT_TYPE,
        stored_extension=_JPEG_EXTENSION,
        size_bytes=len(payload),
    )


def _encode_normalized_image(image: Image.Image, *, keep_png: bool) -> tuple[bytes, str, str]:
    image.info.pop("icc_profile", None)
    image.info.pop("exif", None)
    buffer = io.BytesIO()
    if keep_png:
        image.save(buffer, format="PNG", optimize=True)
        payload = buffer.getvalue()
        return payload, _PNG_CONTENT_TYPE, _PNG_EXTENSION
    if image.mode != "RGB":
        image = image.convert("RGB")
    image.save(
        buffer,
        format="JPEG",
        quality=int(settings.HOUSTON_OBSERVATION_PHOTO_JPEG_QUALITY),
        optimize=True,
        progressive=True,
    )
    payload = buffer.getvalue()
    return payload, _JPEG_CONTENT_TYPE, _JPEG_EXTENSION


def normalize_observation_photo_pair(
    *,
    raw_bytes: bytes,
) -> tuple[NormalizedObservationPhoto, NormalizedObservationPhoto]:
    _ensure_heif_opener_registered()
    payload = b""
    thumbnail: NormalizedObservationPhoto | None = None
    try:
        with Image.open(io.BytesIO(raw_bytes)) as opened:
            opened.load()
            transposed = ImageOps.exif_transpose(opened)
            image = (transposed or opened).copy()
            if getattr(image, "n_frames", 1) > 1:
                image.seek(0)
                image.load()
            image, target_mode = _working_image_and_target_mode(image)
            image = _convert_to_srgb_if_profile_usable(image, target_mode=target_mode)
            if image.mode != target_mode:
                image = image.convert(target_mode)
            keep_png = target_mode == "RGBA"
            image = _resize_without_upscale(image)
            payload, content_type, stored_extension = _encode_normalized_image(
                image,
                keep_png=keep_png,
            )
            thumbnail = _encode_thumbnail(image)
    except InvalidImageContentError:
        raise
    except Exception as exc:
        raise InvalidImageContentError("Invalid image content.") from exc

    if not payload or thumbnail is None or not thumbnail.size_bytes:
        raise InvalidImageContentError("Invalid image content.")

    principal = NormalizedObservationPhoto(
        content_file=ContentFile(payload, name=f"photo.{stored_extension}"),
        content_type=content_type,
        stored_extension=stored_extension,
        size_bytes=len(payload),
    )
    return principal, thumbnail


def normalize_observation_photo(*, raw_bytes: bytes) -> NormalizedObservationPhoto:
    principal, _thumbnail = normalize_observation_photo_pair(raw_bytes=raw_bytes)
    return principal
