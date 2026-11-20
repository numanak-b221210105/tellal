"""The loop that does the work on time: publishes approved posts, then keeps insights and comments fresh.

`tick()` is safe to call as often as you like (from the server's background thread, from cron, or from
the browser). It only ever publishes posts the owner approved.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from . import inbox
from .brand import load_brand
from .db import Store
from .providers import Provider, ProviderError, PublishRequest

MAX_ATTEMPTS = 5
PER_TICK = 5
INSIGHTS_EVERY = 30 * 60
COMMENTS_EVERY = 15 * 60
TOKEN_REFRESH_BEFORE = 10 * 86400

_tick_lock = threading.Lock()


def _account_for(store: Store, post: dict[str, Any]) -> dict[str, Any] | None:
    if post.get("account_id"):
        return store.account(post["account_id"])
    accs = store.accounts()
    return accs[0] if accs else None


def _request(store: Store, post: dict[str, Any], media_url: Callable[[dict[str, Any]], str]) -> PublishRequest:
    media = []
    for mid in post["media_ids"]:
        m = store.media(mid)
        if not m:
            raise ProviderError(f"medya #{mid} kütüphanede yok", retry=False)
        media.append({**m, "url": media_url(m)})
    caption = post.get("caption") or ""
    tags = [t for t in (post.get("hashtags") or []) if f"#{t}".lower() not in caption.lower()]
    if tags and post["format"] != "story":
        caption = (caption + "\n\n" + " ".join(f"#{t}" for t in tags)).strip()
    return PublishRequest(
        format=post["format"],
        media=media,
        caption=caption,
        alt_text=post.get("alt_text") or "",
        cover_ms=post.get("cover_ms"),
        ai_label=bool(post.get("ai_label")),
        first_comment=post.get("first_comment") or "",
        extra=post.get("extra") or {},
    )


def publish_one(
    store: Store,
    post: dict[str, Any],
    provider: Provider,
    media_url: Callable[[dict[str, Any]], str],
    now: float | None = None,
) -> str:
    now = now or time.time()
    acc = _account_for(store, post)
    if not acc:
        store.update_post(post["id"], next_try=now + 3600, error="Bağlı hesap yok.")
        return "no_account"
    pid = post["id"]
    try:
        req = _request(store, post, media_url)
        pending = (post.get("extra") or {}).get("container")
        if pending:
            res = provider.resume(acc, pending, req)
        else:
            q = provider.quota(acc)
            if q["used"] >= q["limit"]:
                store.update_post(
                    pid, next_try=now + 3600, error="24 saatlik paylaşım sınırına ulaşıldı, bir saat sonra denenecek."
                )
                return "quota"
            store.update_post(pid, status="publishing", attempts=(post.get("attempts") or 0) + 1)
            res = provider.publish(acc, req)
    except ProviderError as e:
        attempts = (post.get("attempts") or 0) + (0 if (post.get("extra") or {}).get("container") else 1)
        if e.retry and attempts < MAX_ATTEMPTS:
            wait = min(6 * 3600, 300 * 2 ** (attempts - 1))
            store.update_post(
                pid,
                status="approved",
                attempts=attempts,
                next_try=now + wait,
                error=str(e),
                extra={k: v for k, v in (post.get("extra") or {}).items() if k != "container"},
            )
            store.log("retry", f"Paylaşım ertelendi ({attempts}/{MAX_ATTEMPTS}): {e}", pid)
            return "retry"
        store.update_post(pid, status="failed", error=str(e), attempts=attempts)
        store.log("failed", f"Paylaşılamadı: {e}", pid)
        return "failed"
    if res.pending:
        store.update_post(
            pid, status="publishing", next_try=now + 60, extra={**(post.get("extra") or {}), "container": res.pending}
        )
        return "processing"
    extra = {k: v for k, v in (post.get("extra") or {}).items() if k != "container"}
    store.update_post(
        pid,
        status="published",
        published_at=now,
        remote_id=res.remote_id,
        permalink=res.permalink,
        error=None,
        next_try=None,
        extra=extra,
        account_id=acc["id"],
    )
    store.log(
        "published",
        {"post": "Gönderi", "carousel": "Kaydırmalı gönderi", "reel": "Reels", "story": "Hikâye"}[post["format"]]
        + " paylaşıldı.",
        pid,
    )
    return "published"


def refresh_insights(store: Store, provider: Provider, now: float, days: int = 14) -> int:
    n = 0
    for p in store.posts(status="published", since=now - days * 86400):
        acc = _account_for(store, p)
        if not acc or not p.get("remote_id"):
            continue
        try:
            m = provider.insights(acc, p["remote_id"], p["format"], p["published_at"], post=p)
        except ProviderError:
            continue
        store.save_insights(p["id"], **m)
        n += 1
    return n


def pull_comments(store: Store, provider: Provider, now: float, days: int = 7) -> int:
    brand = load_brand(store)
    n = 0
    for p in store.posts(status="published", since=now - days * 86400):
        acc = _account_for(store, p)
        if not acc or not p.get("remote_id") or p["format"] == "story":
            continue
        try:
            items = provider.comments(acc, p["remote_id"], p["published_at"])
        except ProviderError:
            continue
        for c in items:
            intent = inbox.classify(c["text"])
            cid = store.add_comment(
                post_id=p["id"],
                remote_id=c["remote_id"],
                username=c.get("username"),
                text=c["text"],
                ts=c.get("ts") or now,
                intent=intent,
                status="spam" if intent == "spam" else "open",
            )
            if cid:
                store.update_comment(cid, reply_draft=inbox.draft_reply({**c, "intent": intent}, brand, p))
                n += 1
    return n


def refresh_tokens(store: Store, provider: Provider, now: float) -> None:
    if not hasattr(provider, "refresh_token"):
        return
    for a in store.accounts():
        if (
            a["provider"] == "instagram"
            and a.get("token")
            and a.get("token_expires")
            and a["token_expires"] - now < TOKEN_REFRESH_BEFORE
        ):
            try:
                tok, exp = provider.refresh_token(a["token"])  # type: ignore[attr-defined]
                store.update_account(a["id"], token=tok, token_expires=exp)
                store.log("token", f"@{a['username']} erişim anahtarı yenilendi.")
            except ProviderError as e:
                store.log("token", f"@{a['username']} anahtarı yenilenemedi: {e}")


def tick(
    store: Store,
    provider: Provider,
    media_url: Callable[[dict[str, Any]], str],
    now: float | None = None,
    force: bool = False,
) -> dict[str, Any]:
    if not _tick_lock.acquire(blocking=False):
        return {"busy": True}
    try:
        now = now or time.time()
        result: dict[str, Any] = {"published": 0, "failed": 0, "retry": 0, "insights": 0, "comments": 0}
        for p in store.due_posts(now)[:PER_TICK]:
            r = publish_one(store, p, provider, media_url, now)
            if r in result:
                result[r] += 1
        last = store.get("last_refresh", {}) or {}
        if force or now - last.get("insights", 0) >= INSIGHTS_EVERY or result["published"]:
            result["insights"] = refresh_insights(store, provider, now)
            last["insights"] = now
        if force or now - last.get("comments", 0) >= COMMENTS_EVERY:
            result["comments"] = pull_comments(store, provider, now)
            last["comments"] = now
        if now - last.get("tokens", 0) >= 86400:
            refresh_tokens(store, provider, now)
            last["tokens"] = now
        store.put("last_refresh", last)
        return result
    finally:
        _tick_lock.release()


class Runner:
    """Background thread for the server: ticks every `interval` seconds."""

    def __init__(self, fn: Callable[[], Any], interval: float = 30):
        self.fn, self.interval = fn, interval
        self._stop = threading.Event()
        self._t: threading.Thread | None = None

    def start(self) -> None:
        if self._t:
            return
        self._t = threading.Thread(target=self._run, name="tellal-scheduler", daemon=True)
        self._t.start()

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                self.fn()
            except Exception as e:  # noqa: BLE001 - keep the loop alive
                print(f"[tellal] scheduler error: {e}")

    def stop(self) -> None:
        self._stop.set()
