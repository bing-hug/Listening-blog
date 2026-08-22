import asyncio
import json
import types

import httpx

from app.config import settings
from app.services.notifiers.weclawbot import WeclawBotNotifier


def _article():
    return types.SimpleNamespace(
        title="新文章标题",
        url="https://example.com/post/1",
        summary="这是摘要内容",
    )


def _source():
    return types.SimpleNamespace(display_name="某博主", platform="wechat_mp")


def _patch_client(monkeypatch, handler):
    """Replace httpx.AsyncClient in the notifier module with a MockTransport-backed fake."""
    transport = httpx.MockTransport(handler)

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("app.services.notifiers.weclawbot.httpx.AsyncClient", FakeAsyncClient)


def test_send_posts_message_to_bot(monkeypatch):
    monkeypatch.setattr(settings, "weclawbot_base_url", "http://weclawbot:26322")

    def handler(request):
        assert request.method == "POST"
        assert str(request.url) == "http://weclawbot:26322/bots/bot_123/messages"
        assert request.headers["Authorization"] == "Bearer test-token"
        body = json.loads(request.content)
        assert body["text"]
        assert "【某博主】发布新文章" in body["text"]
        assert "新文章标题" in body["text"]
        assert "https://example.com/post/1" in body["text"]
        return httpx.Response(200, json={"ok": True, "msg": "success"})

    _patch_client(monkeypatch, handler)
    notifier = WeclawBotNotifier()
    result = asyncio.run(
        notifier.send(
            {"weclawbot_bot_id": "bot_123", "weclawbot_api_token": "test-token"},
            _article(),
            _source(),
        )
    )
    assert result is True


def test_send_non_200_returns_false(monkeypatch):
    monkeypatch.setattr(settings, "weclawbot_base_url", "http://weclawbot:26322")

    _patch_client(monkeypatch, lambda request: httpx.Response(500))
    result = asyncio.run(
        WeclawBotNotifier().send(
            {"weclawbot_bot_id": "bot_123", "weclawbot_api_token": "test-token"},
            _article(),
            _source(),
        )
    )
    assert result is False


def test_send_without_bot_id_skips_request(monkeypatch):
    monkeypatch.setattr(settings, "weclawbot_base_url", "http://weclawbot:26322")

    def fail_if_called(request):  # pragma: no cover
        raise AssertionError("should not send request without a bot_id")

    _patch_client(monkeypatch, fail_if_called)
    result = asyncio.run(
        WeclawBotNotifier().send({"weclawbot_api_token": "test-token"}, _article(), _source())
    )
    assert result is False


def test_send_without_api_token_skips_request(monkeypatch):
    monkeypatch.setattr(settings, "weclawbot_base_url", "http://weclawbot:26322")

    def fail_if_called(request):  # pragma: no cover
        raise AssertionError("should not send request without an api_token")

    _patch_client(monkeypatch, fail_if_called)
    result = asyncio.run(
        WeclawBotNotifier().send({"weclawbot_bot_id": "bot_123"}, _article(), _source())
    )
    assert result is False


def test_send_without_base_url_returns_false(monkeypatch):
    monkeypatch.setattr(settings, "weclawbot_base_url", "")

    _patch_client(monkeypatch, lambda request: (_ for _ in ()).throw(AssertionError("should not send request")))
    result = asyncio.run(
        WeclawBotNotifier().send(
            {"weclawbot_bot_id": "bot_123", "weclawbot_api_token": "test-token"},
            _article(),
            _source(),
        )
    )
    assert result is False
