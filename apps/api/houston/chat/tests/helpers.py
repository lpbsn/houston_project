from __future__ import annotations


def chat_url(establishment_id, suffix: str) -> str:
    return f"/api/v1/establishments/{establishment_id}/chat/{suffix}"


def assert_owner_chat_status_payload(body: dict, *, chat_enabled: bool) -> None:
    assert body["chat_enabled"] is chat_enabled
    assert body["can_access"] is chat_enabled
    assert body["can_create_dm"] is chat_enabled
    assert body["can_create_group"] is chat_enabled
    assert body["can_manage_settings"] is True


def create_dm(api_client, *, token: str, establishment_id, target_membership_id):
    return api_client.post(
        chat_url(establishment_id, "conversations/dm/"),
        {"membership_id": str(target_membership_id)},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )


def create_group(
    api_client,
    *,
    token: str,
    establishment_id,
    title: str,
    membership_ids: list,
):
    return api_client.post(
        chat_url(establishment_id, "conversations/groups/"),
        {"title": title, "membership_ids": [str(item) for item in membership_ids]},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
