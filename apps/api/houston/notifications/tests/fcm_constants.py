from __future__ import annotations

import json

TEST_FCM_SERVICE_ACCOUNT_JSON = json.dumps(
    {
        "type": "service_account",
        "project_id": "houston-test",
        "private_key_id": "test",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIE\n-----END PRIVATE KEY-----\n",
        "client_email": "firebase-adminsdk@houston-test.iam.gserviceaccount.com",
        "client_id": "1",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
)

FCM_PUSH_SETTINGS = {
    "HOUSTON_PUSH_ENABLED": True,
    "HOUSTON_FCM_SERVICE_ACCOUNT_JSON": TEST_FCM_SERVICE_ACCOUNT_JSON,
}
