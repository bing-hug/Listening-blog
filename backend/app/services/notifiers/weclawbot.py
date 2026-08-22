import httpx
from app.config import settings
from app.services.notifiers.base import BaseNotifier


class WeclawBotNotifier(BaseNotifier):
    """个人微信推送 — WeClawBot-API (https://github.com/Cp0204/WeClawBot-API)。

    服务端地址在 .env 中配置（WECLAWBOT_BASE_URL，默认 http://localhost:26322），
    每个微信 Bot 由 bot_id + api_token 标识（用户设置页填写）。
    """

    channel = "weclawbot"

    async def send(self, user_settings: dict, article, source) -> bool:
        bot_id = user_settings.get("weclawbot_bot_id")
        api_token = user_settings.get("weclawbot_api_token")
        if not settings.weclawbot_base_url or not bot_id or not api_token:
            return False
        text = f"【{source.display_name}】发布新文章\n\n{article.title}\n\n{article.url}"
        if article.summary:
            text += f"\n\n{article.summary[:100]}"
        headers = {"Authorization": f"Bearer {api_token}"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.weclawbot_base_url.rstrip('/')}/bots/{bot_id}/messages",
                json={"text": text},
                headers=headers,
                timeout=10,
            )
            return resp.status_code == 200
