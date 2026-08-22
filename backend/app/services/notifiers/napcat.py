import httpx
from app.config import settings
from app.services.notifiers.base import BaseNotifier


class NapCatNotifier(BaseNotifier):
    channel = "napcat"

    async def send(self, user_settings: dict, article, source) -> bool:
        qq_id = user_settings.get("napcat_qq_id")
        if not settings.napcat_base_url or not qq_id:
            return False
        text = f"【{source.display_name}】发布新文章\n\n{article.title}\n\n{article.url}"
        if article.summary:
            text += f"\n\n{article.summary[:100]}"
        headers = {}
        if settings.napcat_access_token:
            headers["Authorization"] = f"Bearer {settings.napcat_access_token}"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.napcat_base_url.rstrip('/')}/send_private_msg",
                json={"user_id": int(qq_id), "message": text},
                headers=headers,
                timeout=10,
            )
            return resp.status_code == 200
