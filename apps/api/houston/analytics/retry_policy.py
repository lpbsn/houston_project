from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalyticsPatternRetryPolicy:
    max_retries: int
    retry_delay_seconds: int


def analytics_pattern_task_retry_policy() -> AnalyticsPatternRetryPolicy:
    from houston.analytics.tasks import classify_signal_pattern_task

    return AnalyticsPatternRetryPolicy(
        max_retries=int(classify_signal_pattern_task.max_retries or 0),
        retry_delay_seconds=int(classify_signal_pattern_task.default_retry_delay or 0),
    )
