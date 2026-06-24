from __future__ import annotations


def test_public_tenancy_exports_importable():
    from houston.establishments.permissions import is_valid_membership
    from houston.establishments.role_constants import ADMIN_ROLES

    assert callable(is_valid_membership)
    assert ADMIN_ROLES


def test_cross_app_modules_import_with_public_tenancy_names():
    import houston.actions.permissions  # noqa: F401
    import houston.chat.access  # noqa: F401
    import houston.chat.permissions  # noqa: F401
    import houston.checklists.permissions  # noqa: F401
    import houston.notifications.permissions  # noqa: F401
    import houston.realtime.access  # noqa: F401
    import houston.realtime.permissions  # noqa: F401
    import houston.signals.permissions  # noqa: F401
