from django.urls import path

from houston.notifications.api.views import (
    NotificationMarkReadView,
    NotificationPreferencesView,
    NotificationsListView,
    NotificationsMarkAllReadView,
    VapidPublicKeyView,
    WebPushSubscriptionRevokeView,
    WebPushSubscriptionUpsertView,
)

urlpatterns = [
    path("push/vapid-public-key/", VapidPublicKeyView.as_view(), name="push-vapid-public-key"),
    path(
        "me/web-push-subscriptions/",
        WebPushSubscriptionUpsertView.as_view(),
        name="web-push-subscriptions-upsert",
    ),
    path(
        "me/web-push-subscriptions/<uuid:subscription_id>/",
        WebPushSubscriptionRevokeView.as_view(),
        name="web-push-subscriptions-revoke",
    ),
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
        ("establishments/<uuid:establishment_id>/notifications/<uuid:notification_id>/mark-read/"),
        NotificationMarkReadView.as_view(),
        name="notification-mark-read",
    ),
]
