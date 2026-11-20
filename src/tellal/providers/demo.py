"""A simulated Instagram account, so the whole app can be tried without a Meta app or a real account.

The numbers are made up but follow how Instagram behaves: Reels reach more non-followers, posts at
lunch and evening hours do better, a "send it to someone" line raises shares, a "save it" line raises
saves, and metrics keep growing for a day or two after posting. Same post, same numbers (seeded)."""

from __future__ import annotations

import hashlib
import math
import random
import re
import time
from typing import Any

from ..clock import hour
from .base import ProviderError, PublishRequest, PublishResult

FORMAT_REACH = {"reel": 2.3, "carousel": 1.35, "post": 1.0, "story": 0.32}
PILLAR = {"urun": 1.0, "surec": 1.25, "ipucu": 1.15, "topluluk": 1.05, "kampanya": 0.9, "kanit": 1.1}
HOUR = [
    0.25,
    0.15,
    0.1,
    0.08,
    0.08,
    0.1,
    0.2,
    0.35,
    0.5,
    0.6,
    0.7,
    0.8,
    1.0,
    1.05,
    0.85,
    0.75,
    0.75,
    0.85,
    0.95,
    1.15,
    1.25,
    1.2,
    0.9,
    0.5,
]

COMMENTS = [
    ("fiyat", "Fiyatı ne kadar?"),
    ("fiyat", "fiyat bilgisi alabilir miyim"),
    ("fiyat", "Kaç TL?"),
    ("stok", "Başka rengi var mı?"),
    ("stok", "Stokta var mı hâlâ?"),
    ("stok", "beden seçenekleri neler"),
    ("siparis", "Nasıl sipariş verebilirim?"),
    ("siparis", "Kargo var mı İzmir'e?"),
    ("siparis", "Kapıda ödeme oluyor mu"),
    ("ovgu", "Çok güzel olmuş 😍"),
    ("ovgu", "Bayıldım!"),
    ("ovgu", "Emeğinize sağlık 👏"),
    ("ovgu", "Harika ❤️"),
    ("sikayet", "Siparişim hâlâ gelmedi, 10 gün oldu."),
    ("soru", "Hafta sonu açık mısınız?"),
    ("spam", "Takipçi kazanmak ister misin? Profilime bak 🔥"),
]
NAMES = [
    "ayse.k",
    "mehmet_34",
    "zeynep.design",
    "can.yilmaz",
    "elif_ozt",
    "burak.dmr",
    "selin.atolye",
    "emre.kaya",
    "deniz_ak",
    "merve.sahin",
    "ali.can",
    "ece.tasarim",
]


def _rng(*parts: Any) -> random.Random:
    return random.Random(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest())


class DemoProvider:
    name = "demo"

    def __init__(self, tz_name: str = "Europe/Istanbul", fail_rate: float = 0.0):
        self.tz_name = tz_name
        self.fail_rate = fail_rate
        self._published: dict[str, dict[str, Any]] = {}

    def profile(self, account: dict[str, Any]) -> dict[str, Any]:
        return {
            "remote_id": account.get("remote_id") or "demo",
            "username": account.get("username") or "demo.magaza",
            "name": account.get("name") or "Demo Mağaza",
            "followers": account.get("followers") or 2400,
            "picture": "",
        }

    def quota(self, account: dict[str, Any]) -> dict[str, int]:
        return {"used": 0, "limit": 100}

    def publish(self, account: dict[str, Any], req: PublishRequest) -> PublishResult:
        if not req.media:
            raise ProviderError("no media", retry=False)
        if self.fail_rate and random.random() < self.fail_rate:
            raise ProviderError("simulated network error", retry=True)
        rid = f"demo_{int(time.time() * 1000)}_{random.randint(100, 999)}"
        self._published[rid] = {"format": req.format}
        return PublishResult(remote_id=rid, permalink="")

    def resume(self, account: dict[str, Any], pending: str, req: PublishRequest) -> PublishResult:
        return PublishResult(remote_id=pending)

    # ------------------------------------------------------------------
    def simulate(self, post: dict[str, Any], followers: int, now: float | None = None) -> dict[str, int]:
        """Metrics for a post as of `now`. Pure function of the post, so history can be generated too."""
        now = now or time.time()
        pub = post.get("published_at") or now
        age_h = max(0.0, (now - pub) / 3600)
        fmt = post.get("format", "post")
        cap = (post.get("caption") or "").lower()
        r = _rng(post.get("remote_id") or post.get("id"), "base")
        growth = 1 - math.exp(-age_h / (6 if fmt == "story" else 16))
        if fmt == "story" and age_h > 24:
            growth = 1.0 - math.exp(-24 / 6)
        h = hour(pub, self.tz_name)
        quality = r.uniform(0.6, 1.5) * PILLAR.get(post.get("pillar") or "urun", 1.0)
        quality *= 1.1 if 40 <= len(cap) <= 600 else 0.9
        quality *= 1.0 + 0.04 * min(5, len(post.get("hashtags") or []))
        reach_full = followers * 0.28 * FORMAT_REACH.get(fmt, 1.0) * HOUR[h] * quality
        if fmt == "reel":
            reach_full *= r.choice([1, 1, 1, 1.4, 2.5])  # sometimes a Reel travels
        reach = int(reach_full * growth)
        views = int(reach * (1.9 if fmt == "reel" else 1.25 if fmt == "carousel" else 1.1))
        like_rate = r.uniform(0.03, 0.07) * (1.1 if fmt == "carousel" else 1.0)
        send_rate = r.uniform(0.002, 0.008) * (2.6 if re.search(r"gönder|ilet|send", cap) else 1.0)
        save_rate = (
            r.uniform(0.002, 0.01)
            * (2.4 if re.search(r"kaydet|save", cap) else 1.0)
            * (1.6 if post.get("pillar") == "ipucu" else 1.0)
        )
        comment_rate = r.uniform(0.002, 0.006) * (
            2.2 if "?" in cap.split("\n", 1)[0] or post.get("pillar") == "topluluk" else 1.0
        )
        out = {
            "reach": reach,
            "views": views,
            "likes": int(reach * like_rate),
            "comments": int(reach * comment_rate),
            "saves": int(reach * save_rate),
            "shares": int(reach * send_rate),
            "follows": int(reach * r.uniform(0.001, 0.004) * (1.8 if fmt == "reel" else 1)),
            "profile_visits": int(reach * r.uniform(0.01, 0.03)),
            "avg_watch_ms": int(r.uniform(3500, 9500) * min(1.3, quality)) if fmt == "reel" else 0,
        }
        if fmt == "story":
            out.update(likes=0, comments=0, saves=0)
        return out

    def insights(
        self, account: dict[str, Any], remote_id: str, fmt: str, published_at: float, post: dict[str, Any] | None = None
    ) -> dict[str, int]:
        p = dict(post or {}, remote_id=remote_id, format=fmt, published_at=published_at)
        return self.simulate(p, int(account.get("followers") or 2400))

    def comments(
        self, account: dict[str, Any], remote_id: str, published_at: float, count: int | None = None
    ) -> list[dict[str, Any]]:
        r = _rng(remote_id, "comments")
        age_h = max(0.0, (time.time() - published_at) / 3600)
        n = count if count is not None else min(6, int(r.uniform(1, 6) * (1 - math.exp(-age_h / 10))))
        out = []
        for i in range(n):
            intent, text = r.choice(COMMENTS)
            out.append(
                {
                    "remote_id": f"{remote_id}_c{i}",
                    "username": r.choice(NAMES),
                    "text": text,
                    "ts": published_at + 600 + i * r.uniform(900, 7200),
                    "_intent": intent,
                }
            )
        return out

    def reply(self, account: dict[str, Any], comment_remote_id: str, text: str) -> str:
        return f"{comment_remote_id}_r"
