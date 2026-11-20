"""Instagram API with Instagram Login (graph.instagram.com).

Publishing is a two-step flow: create a media container from a public media URL, wait until Instagram
has processed it (videos take a while), then publish it. Containers expire after 24 hours, and an
account can publish a limited number of posts per 24 hours (checked through content_publishing_limit).

Required permissions: instagram_business_basic, instagram_business_content_publish,
instagram_business_manage_comments, instagram_business_manage_insights. The account must be a
professional (business or creator) account.
"""

from __future__ import annotations

import contextlib
import time
from typing import Any

import httpx

from .base import ProviderError, PublishRequest, PublishResult

GRAPH = "https://graph.instagram.com"
RETRYABLE_CODES = {1, 2, 4, 9, 17, 32, 341, 368, 613}
AUTH_CODES = {102, 190}

INSIGHT_METRICS = {
    "post": ["reach", "views", "likes", "comments", "saved", "shares", "follows", "profile_visits"],
    "carousel": ["reach", "views", "likes", "comments", "saved", "shares", "follows", "profile_visits"],
    "reel": ["reach", "views", "likes", "comments", "saved", "shares", "ig_reels_avg_watch_time"],
    "story": ["reach", "views", "shares", "replies", "follows", "profile_visits"],
}
BASIC_METRICS = ["reach", "likes", "comments", "saved", "shares"]
RENAME = {"saved": "saves", "ig_reels_avg_watch_time": "avg_watch_ms", "replies": "comments"}


class InstagramProvider:
    name = "instagram"

    def __init__(self, settings, transport: httpx.BaseTransport | None = None, sleep=time.sleep):  # noqa: ANN001
        self.version = settings.ig_api_version
        self.client = httpx.Client(base_url=GRAPH, timeout=30, transport=transport)
        self.sleep = sleep

    # ------------------------------------------------------------------ http
    def _call(self, method: str, path: str, token: str, **params: Any) -> dict[str, Any]:
        params = {k: v for k, v in params.items() if v is not None and v != ""}
        params["access_token"] = token
        url = path if path.startswith("/refresh") else f"/{self.version}{path}"
        try:
            if method == "GET":
                r = self.client.get(url, params=params)
            else:
                r = self.client.post(url, data=params)
        except httpx.HTTPError as e:
            raise ProviderError(f"Instagram'a ulaşılamadı: {e}", retry=True, code="network") from e
        try:
            body = r.json()
        except ValueError:
            body = {}
        if r.status_code >= 400 or "error" in body:
            err = body.get("error") or {}
            code = int(err.get("code") or 0)
            msg = err.get("error_user_msg") or err.get("message") or f"HTTP {r.status_code}"
            retry = bool(err.get("is_transient")) or code in RETRYABLE_CODES or r.status_code >= 500
            if code in AUTH_CODES:
                raise ProviderError(
                    f"Instagram oturumu geçersiz, hesabı yeniden bağlayın ({msg})", retry=False, code="auth"
                )
            raise ProviderError(msg, retry=retry, code=str(err.get("error_subcode") or code or r.status_code))
        return body

    @staticmethod
    def _token(account: dict[str, Any]) -> str:
        if not account.get("token"):
            raise ProviderError("Hesap bağlı değil.", retry=False, code="auth")
        return str(account["token"])

    # ------------------------------------------------------------------ account
    def profile(self, account: dict[str, Any]) -> dict[str, Any]:
        b = self._call(
            "GET",
            "/me",
            self._token(account),
            fields="user_id,username,name,profile_picture_url,followers_count,account_type",
        )
        return {
            "remote_id": str(b.get("user_id") or b.get("id")),
            "username": b.get("username", ""),
            "name": b.get("name", ""),
            "picture": b.get("profile_picture_url", ""),
            "followers": int(b.get("followers_count") or 0),
            "account_type": b.get("account_type", ""),
        }

    def quota(self, account: dict[str, Any]) -> dict[str, int]:
        b = self._call(
            "GET",
            f"/{account['remote_id']}/content_publishing_limit",
            self._token(account),
            fields="quota_usage,config",
        )
        d = (b.get("data") or [{}])[0]
        return {"used": int(d.get("quota_usage") or 0), "limit": int((d.get("config") or {}).get("quota_total") or 100)}

    def refresh_token(self, token: str) -> tuple[str, float]:
        b = self._call("GET", "/refresh_access_token", token, grant_type="ig_refresh_token")
        return b["access_token"], time.time() + float(b.get("expires_in") or 5_184_000)

    # ------------------------------------------------------------------ publishing
    def _container(self, account: dict[str, Any], **params: Any) -> str:
        b = self._call("POST", f"/{account['remote_id']}/media", self._token(account), **params)
        return str(b["id"])

    def _status(self, account: dict[str, Any], container: str) -> str:
        b = self._call("GET", f"/{container}", self._token(account), fields="status_code,status")
        code = b.get("status_code", "")
        if code in {"ERROR", "EXPIRED"}:
            raise ProviderError(f"Instagram medyayı işleyemedi: {b.get('status') or code}", retry=False, code=code)
        return code

    def _media_params(self, m: dict[str, Any], fmt: str) -> dict[str, Any]:
        if m["kind"] == "video":
            return {"video_url": m["url"], "media_type": {"reel": "REELS", "story": "STORIES"}.get(fmt, "VIDEO")}
        p = {"image_url": m["url"]}
        if fmt == "story":
            p["media_type"] = "STORIES"
        return p

    def publish(self, account: dict[str, Any], req: PublishRequest) -> PublishResult:
        if not req.media:
            raise ProviderError("Medya yok.", retry=False)
        ai = "true" if req.ai_label else None
        if req.format == "carousel":
            children = []
            for m in req.media:
                p = self._media_params(m, "carousel")
                p["is_carousel_item"] = "true"
                children.append(self._container(account, **p))
            for c in children:
                self._wait(account, c, budget_s=60)
            container = self._container(
                account, media_type="CAROUSEL", children=",".join(children), caption=req.caption, is_ai_generated=ai
            )
        elif req.format == "reel":
            p = self._media_params(req.media[0], "reel")
            container = self._container(
                account, **p, caption=req.caption, share_to_feed="true", thumb_offset=req.cover_ms, is_ai_generated=ai
            )
        elif req.format == "story":
            container = self._container(account, **self._media_params(req.media[0], "story"))
        else:
            container = self._container(
                account,
                image_url=req.media[0]["url"],
                caption=req.caption,
                alt_text=req.alt_text or None,
                is_ai_generated=ai,
            )
        return self.resume(account, container, req, budget_s=20)

    def _wait(self, account: dict[str, Any], container: str, budget_s: float) -> bool:
        deadline = time.monotonic() + budget_s
        while True:
            if self._status(account, container) == "FINISHED":
                return True
            if time.monotonic() >= deadline:
                return False
            self.sleep(3)

    def resume(self, account: dict[str, Any], pending: str, req: PublishRequest, budget_s: float = 5) -> PublishResult:
        if not self._wait(account, pending, budget_s):
            return PublishResult(pending=pending)
        b = self._call("POST", f"/{account['remote_id']}/media_publish", self._token(account), creation_id=pending)
        media_id = str(b["id"])
        permalink = ""
        with contextlib.suppress(ProviderError):
            permalink = self._call("GET", f"/{media_id}", self._token(account), fields="permalink").get("permalink", "")
        if req.first_comment and req.format != "story":
            # The post is live; a missing first comment is not worth failing it.
            with contextlib.suppress(ProviderError):
                self._call("POST", f"/{media_id}/comments", self._token(account), message=req.first_comment)
        return PublishResult(remote_id=media_id, permalink=permalink)

    # ------------------------------------------------------------------ insights and comments
    def insights(
        self, account: dict[str, Any], remote_id: str, fmt: str, published_at: float, post: dict[str, Any] | None = None
    ) -> dict[str, int]:
        token = self._token(account)
        try:
            b = self._call(
                "GET", f"/{remote_id}/insights", token, metric=",".join(INSIGHT_METRICS.get(fmt, BASIC_METRICS))
            )
        except ProviderError as e:
            if e.code not in {"100", "2108006"}:
                raise
            b = self._call("GET", f"/{remote_id}/insights", token, metric=",".join(BASIC_METRICS))
        out: dict[str, int] = {}
        for item in b.get("data", []):
            name = item.get("name", "")
            if "total_value" in item:
                v = item["total_value"].get("value", 0)
            else:
                vals = item.get("values") or [{}]
                v = vals[-1].get("value", 0)
            out[RENAME.get(name, name)] = int(v or 0)
        return out

    def comments(self, account: dict[str, Any], remote_id: str, published_at: float) -> list[dict[str, Any]]:
        b = self._call(
            "GET", f"/{remote_id}/comments", self._token(account), fields="id,text,username,timestamp", limit=50
        )
        out = []
        for c in b.get("data", []):
            ts = c.get("timestamp") or ""
            try:
                from datetime import datetime

                t = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z").timestamp()
            except ValueError:
                t = time.time()
            out.append({"remote_id": c["id"], "username": c.get("username", ""), "text": c.get("text", ""), "ts": t})
        return out

    def reply(self, account: dict[str, Any], comment_remote_id: str, text: str) -> str:
        b = self._call("POST", f"/{comment_remote_id}/replies", self._token(account), message=text)
        return str(b.get("id", ""))
