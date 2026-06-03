from __future__ import annotations


def test_signal_stack_imports_without_cycle():
    import houston.ai.observation_pipeline  # noqa: F401
    import houston.signals.api.serializers  # noqa: F401
    import houston.signals.services  # noqa: F401
