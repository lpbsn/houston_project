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


class BrainAccessDenied(Exception):
    """The actor may not know whether a Brain work exists."""

    code = "brain_access_denied"
    message = "Accès refusé."

    def __init__(self):
        super().__init__(self.message)


class BrainCapacityUnavailable(Exception):
    code = "brain_capacity_unavailable"
    message = "La capacité d'analyse est atteinte."

    def __init__(self):
        super().__init__(self.message)


class BrainWorkError(Exception):
    def __init__(self, *, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class CaptureTimeout(BrainWorkError):
    def __init__(self):
        super().__init__(
            code="capture_timeout",
            message="La capture a dépassé le temps autorisé.",
        )


class CaptureVolumeExceeded(BrainWorkError):
    def __init__(self, category: str):
        self.category = category
        super().__init__(
            code="capture_volume_exceeded",
            message=f"La catégorie « {category} » dépasse le plafond de collecte.",
        )
