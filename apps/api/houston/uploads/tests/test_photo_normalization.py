from __future__ import annotations

import io
import struct

import pytest
from django.conf import settings
from houston.uploads.photo_normalization import normalize_observation_photo
from PIL import Image
from PIL.ExifTags import IFD
from PIL.TiffImagePlugin import IFDRational


def _jpeg_bytes(
    *,
    size: tuple[int, int] = (12, 12),
    color: tuple[int, int, int] = (255, 0, 0),
    exif: Image.Exif | None = None,
    icc_profile: bytes | None = None,
) -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGB", size, color=color)
    save_kwargs: dict = {"format": "JPEG", "quality": 95}
    if exif is not None:
        save_kwargs["exif"] = exif
    if icc_profile is not None:
        save_kwargs["icc_profile"] = icc_profile
    image.save(buffer, **save_kwargs)
    return buffer.getvalue()


def _png_bytes(
    *,
    mode: str,
    size: tuple[int, int],
    color,
    icc_profile: bytes | None = None,
) -> bytes:
    buffer = io.BytesIO()
    save_kwargs: dict = {"format": "PNG"}
    if icc_profile is not None:
        save_kwargs["icc_profile"] = icc_profile
    Image.new(mode, size, color=color).save(buffer, **save_kwargs)
    return buffer.getvalue()


def _s15fixed16(value: float) -> bytes:
    return struct.pack(">i", int(round(value * 65536)))


def _linear_rgb_icc_profile() -> bytes:
    """Compact ICC v2 RGB fixture: D65, sRGB primaries, gamma 1.0 TRC.

    Same primaries as sRGB with a linear curve instead of ~2.2, so midtones
    shift under ImageCms conversion to sRGB. Test-only; not a general ICC writer.
    """

    def xyz_type(x: float, y: float, z: float) -> bytes:
        return b"XYZ " + struct.pack(">I", 0) + _s15fixed16(x) + _s15fixed16(y) + _s15fixed16(z)

    curve = b"curv" + struct.pack(">II", 0, 1) + struct.pack(">H", 256)
    records = (
        (b"wtpt", xyz_type(0.96422, 1.0, 0.82521)),
        (b"rXYZ", xyz_type(0.4360747, 0.2225045, 0.0139322)),
        (b"gXYZ", xyz_type(0.3850649, 0.7168786, 0.0971045)),
        (b"bXYZ", xyz_type(0.1430804, 0.0606169, 0.7141733)),
        (b"rTRC", curve),
        (b"gTRC", curve),
        (b"bTRC", curve),
    )
    table_size = 4 + 12 * len(records)
    chunks: list[bytes] = []
    table = [struct.pack(">I", len(records))]
    offset = 128 + table_size
    for signature, payload in records:
        pad = (-offset) % 4
        if pad:
            chunks.append(b"\x00" * pad)
            offset += pad
        table.append(signature + struct.pack(">II", offset, len(payload)))
        chunks.append(payload)
        offset += len(payload)
    body = b"".join(table) + b"".join(chunks)
    header = bytearray(128)
    struct.pack_into(">I", header, 0, 128 + len(body))
    header[4:8] = b"NONE"
    struct.pack_into(">I", header, 8, 0x02100000)
    header[12:24] = b"mntrRGB XYZ "
    header[36:40] = b"acsp"
    header[68:80] = _s15fixed16(0.96422) + _s15fixed16(1.0) + _s15fixed16(0.82521)
    return bytes(header) + body


def _jpeg_q82(image: Image.Image) -> bytes:
    working = image.convert("RGB")
    working.info.pop("icc_profile", None)
    buffer = io.BytesIO()
    working.save(
        buffer,
        format="JPEG",
        quality=int(settings.HOUSTON_OBSERVATION_PHOTO_JPEG_QUALITY),
        optimize=True,
        progressive=True,
    )
    return buffer.getvalue()


def _pixel(image: Image.Image) -> tuple[int, int, int]:
    pixel = image.convert("RGB").getpixel((0, 0))
    assert isinstance(pixel, tuple) and len(pixel) == 3
    return pixel[0], pixel[1], pixel[2]


def test_exif_orientation_6_transposes_geometry_and_strips_orientation_and_gps():
    exif = Image.Exif()
    exif[0x0112] = 6
    gps_ifd = exif.get_ifd(IFD.GPSInfo)
    gps_ifd[1] = "N"
    gps_ifd[2] = (IFDRational(48, 1), IFDRational(51, 1), IFDRational(0, 1))
    gps_ifd[3] = "E"
    gps_ifd[4] = (IFDRational(2, 1), IFDRational(20, 1), IFDRational(0, 1))

    normalized = normalize_observation_photo(
        raw_bytes=_jpeg_bytes(size=(60, 30), exif=exif),
    )

    with Image.open(io.BytesIO(normalized.content_file.read())) as image:
        assert image.size == (30, 60)
        output_exif = image.getexif()
        assert output_exif.get(0x0112) in {None, 1}
        assert 0x8825 not in output_exif


def _rgb_distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> int:
    return sum((a - b) ** 2 for a, b in zip(left, right, strict=True))


def test_known_icc_profile_is_converted_to_srgb_and_saved_without_embedded_icc():
    from PIL import ImageCms

    source_color = (128, 64, 32)
    icc_profile = _linear_rgb_icc_profile()
    raw_bytes = _png_bytes(
        mode="RGB",
        size=(24, 24),
        color=source_color,
        icc_profile=icc_profile,
    )

    with Image.open(io.BytesIO(raw_bytes)) as source:
        source.load()
        working = source.convert("RGB")
        embedded = source.info.get("icc_profile")
        assert embedded
        converted = ImageCms.profileToProfile(
            working,
            ImageCms.ImageCmsProfile(io.BytesIO(embedded)),
            ImageCms.createProfile("sRGB"),
            outputMode="RGB",
        )
        converted.info.pop("icc_profile", None)
        stripped = working.copy()
        stripped.info.pop("icc_profile", None)
        expected_pixel = _pixel(converted)
        ignored_pixel = _pixel(stripped)
        assert expected_pixel != ignored_pixel
        expected_jpeg = _jpeg_q82(converted)
        naive_jpeg = _jpeg_q82(stripped)

    normalized = normalize_observation_photo(raw_bytes=raw_bytes)
    with Image.open(io.BytesIO(normalized.content_file.read())) as image:
        assert not image.info.get("icc_profile")
        output_pixel = _pixel(image)

    with Image.open(io.BytesIO(expected_jpeg)) as expected_image:
        expected_jpeg_pixel = _pixel(expected_image)
    with Image.open(io.BytesIO(naive_jpeg)) as naive_image:
        naive_jpeg_pixel = _pixel(naive_image)

    assert output_pixel != naive_jpeg_pixel
    assert _rgb_distance(output_pixel, expected_jpeg_pixel) < _rgb_distance(
        output_pixel,
        naive_jpeg_pixel,
    )
    assert _rgb_distance(output_pixel, expected_pixel) < _rgb_distance(
        output_pixel,
        ignored_pixel,
    )


def test_embedded_icc_is_stripped_when_imagecms_unavailable(monkeypatch):
    monkeypatch.setattr("houston.uploads.photo_normalization.ImageCms", None)
    source_color = (128, 64, 32)
    raw_bytes = _png_bytes(
        mode="RGB",
        size=(24, 24),
        color=source_color,
        icc_profile=_linear_rgb_icc_profile(),
    )
    stripped = Image.new("RGB", (24, 24), color=source_color)
    naive_jpeg = _jpeg_q82(stripped)

    normalized = normalize_observation_photo(raw_bytes=raw_bytes)
    payload = normalized.content_file.read()
    assert normalized.content_type == "image/jpeg"
    with Image.open(io.BytesIO(payload)) as image:
        assert not image.info.get("icc_profile")
        output_pixel = _pixel(image)
    with Image.open(io.BytesIO(naive_jpeg)) as naive_image:
        assert output_pixel == _pixel(naive_image)


def test_jpeg_without_icc_profile_normalizes_successfully():
    normalized = normalize_observation_photo(raw_bytes=_jpeg_bytes())
    payload = normalized.content_file.read()
    assert normalized.content_type == "image/jpeg"
    assert normalized.stored_extension == "jpg"
    assert normalized.size_bytes == len(payload)
    assert payload[:2] == b"\xff\xd8"


def test_large_image_is_resized_to_max_edge_without_upscaling_small_image():
    large = normalize_observation_photo(raw_bytes=_jpeg_bytes(size=(3000, 2000)))
    with Image.open(io.BytesIO(large.content_file.read())) as image:
        assert max(image.size) == 1600
        assert image.size[0] == 1600
        assert image.size[1] in {1066, 1067}

    small = normalize_observation_photo(raw_bytes=_jpeg_bytes(size=(800, 600)))
    with Image.open(io.BytesIO(small.content_file.read())) as image:
        assert image.size == (800, 600)


def test_png_with_useful_alpha_stays_png_with_transparency():
    normalized = normalize_observation_photo(
        raw_bytes=_png_bytes(mode="RGBA", size=(16, 16), color=(10, 20, 30, 80)),
    )
    assert normalized.content_type == "image/png"
    assert normalized.stored_extension == "png"
    with Image.open(io.BytesIO(normalized.content_file.read())) as image:
        assert image.format == "PNG"
        extrema = image.convert("RGBA").getchannel("A").getextrema()
        assert extrema[0] < 255


def test_opaque_png_is_stored_as_jpeg():
    normalized = normalize_observation_photo(
        raw_bytes=_png_bytes(mode="RGB", size=(16, 16), color=(10, 20, 30)),
    )
    assert normalized.content_type == "image/jpeg"
    assert normalized.stored_extension == "jpg"
    payload = normalized.content_file.read()
    assert payload[:2] == b"\xff\xd8"
    assert normalized.size_bytes == len(payload)


def test_heic_is_normalized_to_decodable_jpeg_when_encoder_available():
    pytest.importorskip("pillow_heif")
    import pillow_heif

    pillow_heif.register_heif_opener()
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color="green").save(buffer, format="HEIF")
    normalized = normalize_observation_photo(raw_bytes=buffer.getvalue())
    assert normalized.content_type == "image/jpeg"
    payload = normalized.content_file.read()
    assert payload[:2] == b"\xff\xd8"
    with Image.open(io.BytesIO(payload)) as image:
        image.load()
        assert image.format == "JPEG"


def test_normalized_jpeg_is_progressive_and_reports_real_size():
    normalized = normalize_observation_photo(raw_bytes=_jpeg_bytes(size=(32, 32)))
    payload = normalized.content_file.read()
    assert payload[:2] == b"\xff\xd8"
    assert normalized.size_bytes == len(payload)
    with Image.open(io.BytesIO(payload)) as image:
        assert image.info.get("progressive")
