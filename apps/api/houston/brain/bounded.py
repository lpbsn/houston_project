from __future__ import annotations

import json
import logging
import multiprocessing
import os
import tempfile
from collections.abc import Callable

from houston.brain.errors import ExtractionLimit, ExtractionRejected

logger = logging.getLogger(__name__)

_TIMEOUT = (
    "L'extraction a dépassé le temps imparti. Aucun contenu n'a été tronqué."
)
_MEMORY = (
    "L'extraction a dépassé la mémoire disponible. Aucun contenu n'a été tronqué."
)
_FAILED = "La préparation du fichier a échoué."


def extract_bounded(raw: bytes, source_format: str):
    """Run extraction in a child process so a parser call cannot outlive its caps."""
    from houston.brain.bounds import limits_from_settings
    from houston.brain.records import ExtractionResult

    limits = limits_from_settings()
    if int(limits["timeout_seconds"]) <= 0:
        raise ExtractionLimit(code="extraction_timeout", message=_TIMEOUT)
    message = run_bounded_call(
        _extract_child,
        (raw, source_format, limits),
        timeout_seconds=int(limits["timeout_seconds"]),
        memory_bytes=int(limits["memory_bytes"]),
    )
    return _result_from_payload(message, ExtractionResult)


def run_bounded_call(
    target: Callable,
    args: tuple,
    *,
    timeout_seconds: int,
    memory_bytes: int,
) -> dict:
    if timeout_seconds <= 0:
        raise ExtractionLimit(code="extraction_timeout", message=_TIMEOUT)
    descriptor, result_path = tempfile.mkstemp(prefix="houston-brain-extract-")
    os.close(descriptor)
    context = multiprocessing.get_context("spawn")
    process = context.Process(
        target=_run_target,
        args=(target, args, memory_bytes, result_path),
    )
    process.start()
    try:
        process.join(timeout_seconds)
        if process.is_alive():
            process.kill()
            process.join(5)
            raise ExtractionLimit(code="extraction_timeout", message=_TIMEOUT)
        return _read_result(result_path, process.exitcode)
    finally:
        if process.is_alive():
            process.kill()
            process.join(5)
        if process.exitcode is not None:
            process.close()
        try:
            os.unlink(result_path)
        except OSError:
            pass


def _run_target(target: Callable, args: tuple, memory_bytes: int, result_path: str) -> None:
    import resource

    if memory_bytes > 0:
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    try:
        value = target(*args)
        _write_result(result_path, {"status": "ok", "value": value})
    except ExtractionLimit as exc:
        _write_result(
            result_path,
            {"status": "limit", "code": exc.code, "message": exc.message},
        )
    except ExtractionRejected as exc:
        _write_result(
            result_path,
            {"status": "rejected", "code": exc.code, "message": exc.message},
        )
    except MemoryError:
        _write_result(result_path, {"status": "memory"})
    except Exception as exc:
        _write_result(
            result_path,
            {"status": "failed", "exception_class": type(exc).__name__},
        )


def _extract_child(raw: bytes, source_format: str, limits: dict) -> dict:
    from houston.brain.bounds import ExtractionBudget
    from houston.brain.extract import extract_document

    result = extract_document(raw, source_format, ExtractionBudget(limits))
    return result.as_payload()


def _write_result(path: str, payload: dict) -> None:
    temporary = f"{path}.partial"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    os.replace(temporary, path)


def _read_result(path: str, exitcode: int | None) -> dict:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        if exitcode is not None and exitcode < 0:
            raise ExtractionLimit(code="extraction_memory_limit", message=_MEMORY)
        logger.error(
            "brain_extraction_process_failed",
            extra={
                "event": "brain_extraction_process_failed",
                "exitcode": exitcode,
            },
        )
        raise ExtractionRejected(code="extraction_failed", message=_FAILED)
    with open(path, encoding="utf-8") as handle:
        message = json.load(handle)
    status = message.get("status")
    if status == "ok":
        return message["value"]
    if status == "memory":
        raise ExtractionLimit(code="extraction_memory_limit", message=_MEMORY)
    if status in {"limit", "rejected"}:
        error_type = ExtractionLimit if status == "limit" else ExtractionRejected
        raise error_type(code=message["code"], message=message["message"])
    logger.error(
        "brain_extraction_process_failed",
        extra={
            "event": "brain_extraction_process_failed",
            "exception_class": message.get("exception_class", "Exception"),
        },
    )
    raise ExtractionRejected(code="extraction_failed", message=_FAILED)


def _result_from_payload(payload: dict, result_type):
    from houston.brain.records import Measure, QualitativeBlock

    return result_type(
        source_format=payload["format"],
        measures=[
            Measure(
                label=item["label"],
                value=item["value"],
                value_kind=item["value_kind"],
                unit=item["unit"],
                period=item["period"],
                scope=item["scope"],
                definition=item["definition"],
                locator=item["locator"],
                ambiguities=tuple(item["ambiguities"]),
                raw=item["raw"],
            )
            for item in payload["measures"]
        ],
        qualitative=[
            QualitativeBlock(kind=item["kind"], text=item["text"], locator=item["locator"])
            for item in payload["qualitative"]
        ],
        warnings=payload["warnings"],
    )
