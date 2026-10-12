import pytest

from houston.brain.models import BrainCapacity


@pytest.fixture(autouse=True)
def brain_capacity_row(db):
    """Transaction tests flush the migrated singleton. Put it back before each test."""
    BrainCapacity.objects.get_or_create(singleton_key=1)
