from __future__ import annotations


class BrainPreparationError(Exception):
    def __init__(self, *, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class ReportingRejected(BrainPreparationError):
    """The file is refused before a reporting row or a stored original exists."""


class ExtractionRejected(BrainPreparationError):
    """Preparation failed after the original was stored. The reporting is rejected."""


class ExtractionLimit(ExtractionRejected):
    """A technical ceiling was hit. Nothing partial is kept as a successful extraction."""
