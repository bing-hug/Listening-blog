import asyncio, uuid, json, logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.config import settings
from app.models.article import Article
from app.models.source import Source
from app.models.subscription import Subscription
from app.models.user import User
from app.models.push_subscription import PushSubscription
from app.services.notifiers.dispatcher import dispatcher
from app.tasks.celery_app import celery_app
from app.tasks.db import session_factory as _session_factory
import redis as redis_lib

logger = logging.getLogger(__name__)

# dnd_start/dnd_end come from the UI <input type="time"> as the user's local
# wall clock. The app operates on China time (celery timezone="Asia/Shanghai",
# daily digest at 08:00 Shanghai), which has no DST, so compare against a fixed
# UTC+8 — not UTC, which would shift the quiet window by 8 hours.
_APP_TZ = timezone(timedelta(hours=8))


def _in_dnd(user_settings):
    if not user_settings.get("dnd_enabled"):
        return False
    now = datetime.now(_APP_TZ).strftime("%H:%M")
    start = user_settings.get("dnd_start", "22:00")
    end = user_settings.get("dnd_end", "08:00")
    if start <= end:
        return start <= now <= end
    return now >= start or now <= end

async def _notify(article_id: str, source_id: str):
    async with _session_factory() as db:
        article = (await db.execute(select(Article).where(Article.id == uuid.UUID(article_id)))).scalar_one_or_none()
        source = (await db.execute(select(Source).where(Source.id == uuid.UUID(source_id)))).scalar_one_or_none()
        if not article or not source:
            logger.warning("Notify skipped: article/source not found (article=%s source=%s)", article_id, source_id)
            return

        subs = (await db.execute(
            select(Subscription).where(Subscription.source_id == source.id, Subscription.notify_enabled == True)  # noqa
        )).scalars().all()

        logger.info(
            "[步骤5] 通知任务开始: article=%s (%s) source=%s, 订阅用户 %d 人",
            article.id, (article.title or "")[:50], source.display_name, len(subs),
        )

        if not subs:
            logger.info("[步骤5] 无订阅用户, 跳过通知: article=%s (%s)", article.id, source.display_name)

        r = redis_lib.Redis.from_url(settings.redis_url)
        for sub in subs:
            # Wrap per-user work so one failing user/channel can't abort the run,
            # and the failure still lands in the unified error log.
            try:
                user = (await db.execute(select(User).where(User.id == sub.user_id))).scalar_one()
                user_settings = user.settings or {}

                push_subs = (await db.execute(
                    select(PushSubscription).where(PushSubscription.user_id == user.id)
                )).scalars().all()
                user_settings["push_subscriptions"] = [{"endpoint": p.endpoint, "p256dh": p.p256dh, "auth": p.auth} for p in push_subs]

                channels = sub.notify_channels or user_settings.get("notify_defaults", ["web"])

                if _in_dnd(user_settings) and not sub.dnd_exempt:
                    logger.info("[步骤6] 免打扰时段, 延迟投递: article=%s user=%s channels=%s", article.id, user.id, channels)
                    r.rpush(f"juflow:dnd_pending:{user.id}", json.dumps({"article_id": article_id, "source_id": source_id, "channels": channels}, default=str))
                    continue

                email_digest = user_settings.get("email_digest", "instant")
                if email_digest != "instant" and "email" in channels:
                    r.rpush(f"juflow:email_digest:{user.id}", json.dumps({"article_id": article_id, "source_id": source_id}))
                    channels = [c for c in channels if c != "email"]

                logger.info("[步骤6] 分发通知: article=%s user=%s channels=%s", article.id, user.id, channels)
                await dispatcher.dispatch(user_settings, channels, article, source)

                # WebSocket push always
                msg = {"type": "new_article", "article": {"id": str(article.id), "title": article.title,
                    "summary": (article.summary or "")[:200], "url": article.url,
                    "published_at": str(article.published_at),
                    "source": {"platform": source.platform, "display_name": source.display_name}},
                    "user_ids": [str(user.id)]}
                r.publish("juflow:new_articles", json.dumps(msg, default=str))
            except Exception as e:
                logger.error("Notify failed for user %s (article %s): %s", getattr(sub, "user_id", "?"), article.id, e, exc_info=True)
        r.close()

@celery_app.task(name="app.tasks.notify_task.notify_new_article")
def notify_new_article(article_id: str, source_id: str):
    asyncio.run(_notify(article_id, source_id))
