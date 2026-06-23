from django.urls import path

from houston.notifications.api.views import (
    NotificationArchiveView,
    NotificationMarkReadView,
    NotificationPreferencesView,
    NotificationsListView,
    NotificationsMarkAllReadView,
)

urlpatterns = [
    path(
        "establishments/<uuid:establishment_id>/notifications/",
        NotificationsListView.as_view(),
        name="notifications-list",
    ),
    path(
        "establishments/<uuid:establishment_id>/notifications/preferences/",
        NotificationPreferencesView.as_view(),
        name="notifications-preferences",
    ),
    path(
        "establishments/<uuid:establishment_id>/notifications/mark-all-read/",
        NotificationsMarkAllReadView.as_view(),
        name="notifications-mark-all-read",
    ),
    path(
        (
            "establishments/<uuid:establishment_id>/notifications/"
            "<uuid:notification_id>/mark-read/"
        ),
        NotificationMarkReadView.as_view(),
        name="notification-mark-read",
    ),
    path(
        (
            "establishments/<uuid:establishment_id>/notifications/"
            "<uuid:notification_id>/archive/"
        ),
        NotificationArchiveView.as_view(),
        name="notification-archive",
    ),
]
