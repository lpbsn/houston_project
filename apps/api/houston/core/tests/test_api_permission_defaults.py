from __future__ import annotations

import uuid

from django.urls import get_resolver
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from houston.accounts.api.views import (
    CsrfCookieView,
    DirectorInvitationAcceptView,
    LoginView,
    LogoutView,
    RefreshView,
    RegisterView,
    ValidateOwnerRegistrationView,
)
from houston.core.api.permissions import DenyByDefault
from houston.core.views import ClientRequirementsView, HealthView
from houston.observations.api.media_views import ObservationMediaPreviewView
from houston.testing.factories import create_user

PUBLIC_API_VIEWS = frozenset(
    {
        HealthView,
        ClientRequirementsView,
        CsrfCookieView,
        LoginView,
        RegisterView,
        ValidateOwnerRegistrationView,
        DirectorInvitationAcceptView,
        RefreshView,
        LogoutView,
        ObservationMediaPreviewView,
    }
)


def _iter_routed_api_views(url_patterns):
    for pattern in url_patterns:
        if hasattr(pattern, "url_patterns"):
            yield from _iter_routed_api_views(pattern.url_patterns)
            continue
        callback = getattr(pattern, "callback", None)
        if callback is None:
            continue
        view_cls = getattr(callback, "view_class", None)
        if view_cls is None or not issubclass(view_cls, APIView):
            continue
        yield view_cls, getattr(callback, "initkwargs", {}) or {}


def _permission_class_lists(view_cls, initkwargs: dict) -> list[list[type[BasePermission]]]:
    if "permission_classes" in initkwargs:
        return [list(initkwargs["permission_classes"])]
    get_classes = getattr(view_cls, "permission_classes_get", None)
    post_classes = getattr(view_cls, "permission_classes_post", None)
    if get_classes is not None or post_classes is not None:
        lists: list[list[type[BasePermission]]] = []
        if get_classes is not None:
            lists.append(list(get_classes))
        if post_classes is not None:
            lists.append(list(post_classes))
        return lists
    return [list(view_cls.permission_classes)]


def _is_allow_any_only(permission_classes: list) -> bool:
    return bool(permission_classes) and all(item is AllowAny for item in permission_classes)


def _is_deny_by_omission_only(permission_classes: list) -> bool:
    return permission_classes == [DenyByDefault]


def test_routed_api_views_are_public_allowlist_or_explicitly_guarded():
    routed = list(_iter_routed_api_views(get_resolver().url_patterns))
    assert routed

    public_seen: set[type[APIView]] = set()
    for view_cls, initkwargs in routed:
        permission_lists = _permission_class_lists(view_cls, initkwargs)
        assert permission_lists
        if view_cls in PUBLIC_API_VIEWS:
            public_seen.add(view_cls)
            assert all(_is_allow_any_only(group) for group in permission_lists), view_cls
            continue
        view_name = getattr(view_cls, "__name__", "")
        if view_name in {"SpectacularAPIView", "SpectacularSwaggerView"}:
            assert all(_is_allow_any_only(group) for group in permission_lists), view_cls
            continue
        for group in permission_lists:
            assert group, view_cls
            assert not _is_deny_by_omission_only(group), view_cls
            assert not _is_allow_any_only(group), view_cls

    assert public_seen == PUBLIC_API_VIEWS


def test_default_permission_denies_authenticated_omitted_view(db):
    class ForgottenView(APIView):
        def get(self, request):
            return None

    user = create_user(username=f"forgotten_{uuid.uuid4().hex[:8]}")
    request = APIRequestFactory().get("/forgotten/")
    force_authenticate(request, user=user)
    response = ForgottenView.as_view()(request)
    assert response.status_code == 403
    assert response.data["code"] == "permission_denied"
