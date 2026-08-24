import logging

import httpx
from app.config import settings
from app.services.notifiers.base import BaseNotifier

logger = logging.getLogger(__name__)


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
            logger.warning(
                "WeClawBot skipped: config incomplete (base_url=%s bot_id=%s api_token=%s)",
                bool(settings.weclawbot_base_url), bool(bot_id), bool(api_token),
            )
            return False
        text = f"【{source.display_name}】发布新文章\n\n{article.title}\n\n{article.url}"
        if article.summary:
            text += f"\n\n{article.summary[:100]}"
        headers = {"Authorization": f"Bearer {api_token}"}
        url = f"{settings.weclawbot_base_url.rstrip('/')}/bots/{bot_id}/messages"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    json={"text": text},
                    headers=headers,
                    timeout=10,
                )
        except Exception as e:
            logger.error("WeClawBot request failed (bot_id=%s article=%s): %s", bot_id, getattr(article, "id", None), e, exc_info=True)
            return False
        if resp.status_code != 200:
            logger.error(
                "WeClawBot responded %s for article %s (bot_id=%s): %s",
                resp.status_code, getattr(article, "id", None), bot_id, resp.text[:200],
            )
            return False
        logger.info("WeClawBot message sent (bot_id=%s article=%s)", bot_id, getattr(article, "id", None))
        return True
