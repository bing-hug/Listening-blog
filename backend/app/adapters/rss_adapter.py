import html
import re

from app.adapters.base import ArticleItem, SourceInfo
from app.adapters.rss_base import DirectRssBaseAdapter
from app.adapters.rsshub_base import RsshubBaseAdapter


def _strip_html(text: str | None) -> str:
    """Remove HTML tags from feed text so stored titles/summaries render as plain text."""
    if not text:
        return text or ""
    text = html.unescape(text)  # &lt;p&gt; -> <p>
    text = re.sub(r"<[^>]*>", "", text)
    return re.sub(r"\s+", " ", text).strip()


class CsdnRssAdapter(DirectRssBaseAdapter):
    platform = "csdn"
    name = "CSDN"
    url_pattern = r"https?://blog\.csdn\.net/([^/]+)"
    rss_url_template = "https://blog.csdn.net/{uid}/rss/list"
    home_url_template = "https://blog.csdn.net/{uid}"


# Zhihu has no public RSS — the old /people/{uid}/posts URL is an HTML/API page,
# not a feed, so the previous "direct RSS" adapter always parsed to 0 articles.
# Route through RSSHub instead, like the other RSSHub-backed platforms.
class ZhihuRssAdapter(RsshubBaseAdapter):
    platform = "zhihu"
    name = "知乎"
    url_pattern = r"https?://(?:www\.)?zhihu\.com/(?:people|column)/([^/]+)"
    # RSSHub's /zhihu/posts route is broken against Zhihu's current anti-bot
    # (Zhihu returns 403 for the articles API). /zhihu/people/activities is the
    # only user feed that still works and returns recent content (pins, answers,
    # articles). Columns keep the dedicated /zhihu/zhuanlan route.
    rsshub_route_template = "/zhihu/people/activities/{uid}"
    display_name_template = "{uid}"
    home_url_template = "https://www.zhihu.com/people/{uid}"

    async def resolve(self, url: str) -> SourceInfo:
        match = self._compiled_pattern.match(url)
        if not match:
            raise ValueError(f"Cannot parse Zhihu URL: {url}")
        uid = match.group(1)
        is_column = "/column/" in url
        route = f"/zhihu/zhuanlan/{uid}" if is_column else f"/zhihu/people/activities/{uid}"
        return SourceInfo(
            platform=self.platform,
            platform_uid=uid,
            display_name=uid,
            home_url=f"https://www.zhihu.com/{'column' if is_column else 'people'}/{uid}",
            adapter_type=self.adapter_type,
            adapter_config={"rsshub_route": route, "is_column": is_column},
        )

    async def fetch(self, source: SourceInfo, cookies: str | None = None) -> list[ArticleItem]:
        # The RSSHub activities feed embeds HTML (e.g. <p>…) inside titles and
        # summaries; strip it so the app stores and displays plain text.
        articles = await super().fetch(source, cookies)
        for article in articles:
            article.title = _strip_html(article.title)
            article.summary = _strip_html(article.summary)
        return articles
