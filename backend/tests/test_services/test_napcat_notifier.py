import asyncio
import json
import types

import httpx

from app.config import settings
from app.services.notifiers.napcat import NapCatNotifier


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

    monkeypatch.setattr("app.services.notifiers.napcat.httpx.AsyncClient", FakeAsyncClient)


def test_send_posts_onebot_private_msg(monkeypatch):
    monkeypatch.setattr(settings, "napcat_base_url", "http://napcat:3000")
    monkeypatch.setattr(settings, "napcat_access_token", "test-token")

    def handler(request):
        assert request.method == "POST"
        assert str(request.url) == "http://napcat:3000/send_private_msg"
        assert request.headers["Authorization"] == "Bearer test-token"
        body = json.loads(request.content)
        assert body["user_id"] == 123456789
        assert "【某博主】发布新文章" in body["message"]
        assert "新文章标题" in body["message"]
        assert "https://example.com/post/1" in body["message"]
        return httpx.Response(200, json={"status": "ok", "retcode": 0, "data": {"message_id": 1}})

    _patch_client(monkeypatch, handler)
    notifier = NapCatNotifier()
    result = asyncio.run(notifier.send({"napcat_qq_id": "123456789"}, _article(), _source()))
    assert result is True


def test_send_without_token_omits_auth_header(monkeypatch):
    monkeypatch.setattr(settings, "napcat_base_url", "http://napcat:3000")
    monkeypatch.setattr(settings, "napcat_access_token", "")

    def handler(request):
        assert "Authorization" not in request.headers
        return httpx.Response(200)

    _patch_client(monkeypatch, handler)
    result = asyncio.run(NapCatNotifier().send({"napcat_qq_id": "123456789"}, _article(), _source()))
    assert result is True


def test_send_non_200_returns_false(monkeypatch):
    monkeypatch.setattr(settings, "napcat_base_url", "http://napcat:3000")
    monkeypatch.setattr(settings, "napcat_access_token", "")

    _patch_client(monkeypatch, lambda request: httpx.Response(500))
    result = asyncio.run(NapCatNotifier().send({"napcat_qq_id": "123456789"}, _article(), _source()))
    assert result is False


def test_send_without_qq_id_skips_request(monkeypatch):
    monkeypatch.setattr(settings, "napcat_base_url", "http://napcat:3000")
    monkeypatch.setattr(settings, "napcat_access_token", "test-token")

    def fail_if_called(request):  # pragma: no cover
        raise AssertionError("should not send request without a target QQ")

    _patch_client(monkeypatch, fail_if_called)
    result = asyncio.run(NapCatNotifier().send({}, _article(), _source()))
    assert result is False


def test_send_without_base_url_returns_false(monkeypatch):
    monkeypatch.setattr(settings, "napcat_base_url", "")
    monkeypatch.setattr(settings, "napcat_access_token", "")

    _patch_client(monkeypatch, lambda request: (_ for _ in ()).throw(AssertionError("should not send request")))
    result = asyncio.run(NapCatNotifier().send({"napcat_qq_id": "123456789"}, _article(), _source()))
    assert result is False
