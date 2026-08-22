import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_update_settings_persists_for_existing_settings(client: AsyncClient, auth_headers):
    """Regression: JSONB settings were mutated in place and assigned back, so
    SQLAlchemy emitted no UPDATE and every save after the first was a silent
    no-op. Saving twice must persist the second batch of values."""
    first = {
        "notify_defaults": ["web", "napcat"],
        "dnd_enabled": False,
        "dnd_start": "22:00",
        "dnd_end": "08:00",
        "email_digest": "instant",
        "email_address": "",
        "wechat_webhook": "",
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "napcat_qq_id": "111",
        "weclawbot_bot_id": "bot_one",
        "weclawbot_api_token": "tok_one",
    }
    r1 = await client.put("/api/v1/notifications/settings", json=first, headers=auth_headers)
    assert r1.status_code == 200

    second = dict(first)
    second["napcat_qq_id"] = "222"
    second["weclawbot_bot_id"] = "bot_two"
    second["weclawbot_api_token"] = "tok_two"
    r2 = await client.put("/api/v1/notifications/settings", json=second, headers=auth_headers)
    assert r2.status_code == 200

    got = (await client.get("/api/v1/notifications/settings", headers=auth_headers)).json()
    assert got["napcat_qq_id"] == "222"
    assert got["weclawbot_bot_id"] == "bot_two"
    assert got["weclawbot_api_token"] == "tok_two"


@pytest.mark.asyncio
async def test_update_settings_returns_saved_values(client: AsyncClient, auth_headers):
    payload = {
        "notify_defaults": ["web", "weclawbot"],
        "dnd_enabled": True,
        "dnd_start": "23:00",
        "dnd_end": "07:00",
        "email_digest": "instant",
        "email_address": "a@b.com",
        "wechat_webhook": "",
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "napcat_qq_id": "",
        "weclawbot_bot_id": "my_bot",
        "weclawbot_api_token": "my_token",
    }
    r = await client.put("/api/v1/notifications/settings", json=payload, headers=auth_headers)
    assert r.status_code == 200
    got = (await client.get("/api/v1/notifications/settings", headers=auth_headers)).json()
    assert got["notify_defaults"] == ["web", "weclawbot"]
    assert got["dnd_enabled"] is True
    assert got["weclawbot_bot_id"] == "my_bot"
    assert got["weclawbot_api_token"] == "my_token"
