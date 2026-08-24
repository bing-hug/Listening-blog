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
        logger.info(
            "[步骤7] WeClawBot 发送开始: article=%s 配置(base_url=%s bot_id=%s token=%s)",
            getattr(article, "id", None),
            bool(settings.weclawbot_base_url), bool(bot_id), bool(api_token),
        )
        if not settings.weclawbot_base_url or not bot_id or not api_token:
            logger.warning(
                "[步骤7] WeClawBot 配置不完整, 跳过 (base_url=%s bot_id=%s api_token=%s)",
                bool(settings.weclawbot_base_url), bool(bot_id), bool(api_token),
            )
            return False
        text = f"【{source.display_name}】发布新文章\n\n{article.title}\n\n{article.url}"
        if article.summary:
            text += f"\n\n{article.summary[:100]}"
        headers = {"Authorization": f"Bearer {api_token}"}
        url = f"{settings.weclawbot_base_url.rstrip('/')}/bots/{bot_id}/messages"
        logger.info("[步骤7] WeClawBot POST %s", url)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    json={"text": text},
                    headers=headers,
                    timeout=10,
                )
        except Exception as e:
            logger.error("[步骤7] WeClawBot 请求异常 (bot_id=%s article=%s): %s", bot_id, getattr(article, "id", None), e, exc_info=True)
            return False
        if resp.status_code != 200:
            logger.error(
                "[步骤7] WeClawBot 响应 %s (bot_id=%s article=%s): %s",
                resp.status_code, bot_id, getattr(article, "id", None), resp.text[:200],
            )
            return False
        logger.info(
            "[步骤7] WeClawBot 发送成功: bot_id=%s article=%s (响应 status=%s body=%s)",
            bot_id, getattr(article, "id", None), resp.status_code, resp.text[:200],
        )
        return True
