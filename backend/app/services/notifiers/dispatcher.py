import logging

from app.services.notifiers.web_push import WebPushNotifier
from app.services.notifiers.wechat import WechatNotifier
from app.services.notifiers.telegram import TelegramNotifier
from app.services.notifiers.email_notifier import EmailNotifier
from app.services.notifiers.napcat import NapCatNotifier
from app.services.notifiers.weclawbot import WeclawBotNotifier

logger = logging.getLogger(__name__)

_notifiers = {
    "web_push": WebPushNotifier(),
    "wechat": WechatNotifier(),
    "telegram": TelegramNotifier(),
    "email": EmailNotifier(),
    "napcat": NapCatNotifier(),
    "weclawbot": WeclawBotNotifier(),
}

class NotificationDispatcher:
    async def dispatch(self, user_settings: dict, channels: list[str], article, source) -> None:
        for ch in channels:
            notifier = _notifiers.get(ch)
            if notifier:
                logger.info("[步骤6] 渠道分发: channel=%s (article=%s)", ch, getattr(article, "id", None))
                try:
                    ok = await notifier.send(user_settings, article, source)
                    if not ok:
                        logger.error(
                            "[步骤6] 渠道 %s 发送失败 (article=%s source=%s)",
                            ch, getattr(article, "id", None), getattr(source, "platform", "?"),
                        )
                except Exception as e:
                    logger.error(
                        "[步骤6] 渠道 %s 发送异常 (article=%s source=%s): %s",
                        ch, getattr(article, "id", None), getattr(source, "platform", "?"), e,
                        exc_info=True,
                    )

dispatcher = NotificationDispatcher()
