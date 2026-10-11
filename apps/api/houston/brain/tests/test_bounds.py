from __future__ import annotations

import io
import time
import zipfile

import pytest

from houston.brain.bounded import run_bounded_call
from houston.brain.bounds import ExtractionBudget, _inflated_size
from houston.brain.errors import ExtractionLimit

pytestmark = pytest.mark.django_db


def _allocate(size: int) -> int:
    block = bytearray(size)
    return len(block)


def test_a_blocking_parser_call_is_stopped_at_the_timeout():
    started = time.monotonic()
    with pytest.raises(ExtractionLimit) as refused:
        run_bounded_call(
            time.sleep,
            (30,),
            timeout_seconds=3,
            memory_bytes=512 * 1024 * 1024,
        )
    assert refused.value.code == "extraction_timeout"
    assert time.monotonic() - started < 15


def test_a_parser_call_cannot_grow_past_the_memory_cap():
    with pytest.raises(ExtractionLimit) as refused:
        run_bounded_call(
            _allocate,
            (96 * 1024 * 1024,),
            timeout_seconds=30,
            memory_bytes=64 * 1024 * 1024,
        )
    assert refused.value.code == "extraction_memory_limit"


def test_understated_zip_size_is_capped_while_inflating():
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("xl/workbook.xml", b"A" * 5000)
    budget = ExtractionBudget(
        limits={
            "timeout_seconds": 30,
            "max_uncompressed": 1000,
            "max_zip_entries": 10,
        }
    )
    with zipfile.ZipFile(io.BytesIO(payload.getvalue())) as archive:
        info = archive.infolist()[0]
        info.file_size = 1
        with pytest.raises(ExtractionLimit) as refused:
            _inflated_size(
                archive,
                info,
                budget,
                1000,
                invalid_code="invalid_xlsx",
                invalid_message="invalide",
            )
    assert refused.value.code == "ooxml_uncompressed_too_large"
