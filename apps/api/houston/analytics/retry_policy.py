from __future__ import annotations

from dataclasses import dataclass

# Previous Celery gate: retry while request.retries < 3. That is the first
# execution plus three retries (four provider calls). The delay is the 30s
# countdown those tasks already used.
_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 30


@dataclass(frozen=True)
class AnalyticsPatternRetryPolicy:
    max_retries: int
    retry_delay_seconds: int

    @property
    def max_provider_calls(self) -> int:
        # The first execution plus one call per allowed retry.
        return self.max_retries + 1


def analytics_pattern_task_retry_policy() -> AnalyticsPatternRetryPolicy:
    return AnalyticsPatternRetryPolicy(
        max_retries=_MAX_RETRIES,
        retry_delay_seconds=_RETRY_DELAY_SECONDS,
    )
