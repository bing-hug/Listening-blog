import logging
import re
from datetime import datetime, timezone

import feedparser
import httpx

from app.adapters.base import BaseAdapter, SourceInfo, ArticleItem
from app.config import settings

logger = logging.getLogger(__name__)


class RsshubBaseAdapter(BaseAdapter):
    """Base class for RSSHub-backed adapters. Subclasses only need to declare config."""

    adapter_type = "rsshub"

    # Subclass must set these:
    platform: str
    name: str
    url_pattern: str  # regex with one capture group for the uid
    rsshub_route_template: str  # e.g. "/xueqiu/user/{uid}"
    display_name_template: str  # e.g. "雪球用户{uid}"
    home_url_template: str  # e.g. "https://xueqiu.com/u/{uid}"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "url_pattern") and isinstance(cls.url_pattern, str):
            cls._compiled_pattern = re.compile(cls.url_pattern)

    def detect(self, url: str) -> bool:
        return bool(self._compiled_pattern.match(url))

    async def resolve(self, url: str) -> SourceInfo:
        match = self._compiled_pattern.match(url)
        if not match:
            raise ValueError(f"Cannot parse {self.name} URL: {url}")
        uid = match.group(1)
        return SourceInfo(
            platform=self.platform,
            platform_uid=uid,
            display_name=self.display_name_template.format(uid=uid),
            home_url=self.home_url_template.format(uid=uid),
            adapter_type=self.adapter_type,
            adapter_config={"rsshub_route": self.rsshub_route_template.format(uid=uid)},
        )

    async def fetch(self, source: SourceInfo, cookies: str | None = None) -> list[ArticleItem]:
        route = source.adapter_config.get(
            "rsshub_route", self.rsshub_route_template.format(uid=source.platform_uid)
        )
        rsshub_url = f"{settings.rsshub_url}{route}"
        logger.info("[步骤2] 拉取 %s: 请求 RSSHub %s", source.platform, rsshub_url)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(rsshub_url, timeout=30)
                logger.info("[步骤2] RSSHub 已响应: status=%s (%d 字节)", resp.status_code, len(resp.text))
                resp.raise_for_status()
        except Exception as e:
            logger.error(
                "[步骤2] RSSHub 请求失败 %s (route %s): %s",
                source.platform,
                rsshub_url,
                e,
                exc_info=True,
            )
            raise
        feed = feedparser.parse(resp.text)
        logger.info("[步骤3] 解析 feed: RSSHub 返回 %d 条 entry", len(feed.entries))
        articles = []
        for entry in feed.entries:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            articles.append(ArticleItem(
                title=entry.get("title", ""),
                url=entry.get("link", ""),
                summary=entry.get("summary", ""),
                content=entry.get("content", [{}])[0].get("value") if entry.get("content") else None,
                published_at=published,
            ))
        logger.info("[步骤3] 解析完成: %s 共 %d 条文章", source.platform, len(articles))
        return articles
