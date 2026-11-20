"""Fills an empty install with a made-up leather workshop, six weeks of history and next week's plan,
so every screen has something real to show. Used by demo mode and the in-browser demo."""

from __future__ import annotations

import json
import random
import shutil
import time
from datetime import datetime, timedelta
from importlib import resources
from pathlib import Path
from typing import Any

from . import content, inbox
from .brand import Brand, Product, Rhythm, save_brand
from .clock import at, tz
from .db import Store
from .planner import plan_week
from .providers.demo import DemoProvider

FOLLOWERS = 2380

BRAND = Brand(
    name="Lale Deri Atölyesi",
    handle="lale.deri",
    sector="deri",
    city="Sakarya",
    description="Sakarya'da küçük bir atölye. Çanta, cüzdan ve kemerleri bitkisel tabaklanmış deriden elde dikiyoruz.",
    audience="25–45 yaş, el yapımı ve uzun ömürlü ürün sevenler, hediye arayanlar",
    tone="samimi",
    emoji=1,
    languages=["tr", "en"],
    usps=["Bitkisel tabaklanmış deri, el dikişi", "Her ürüne isim baskısı ücretsiz", "2 yıl dikiş garantisi"],
    products=[
        Product(name="Siyah Tote Çanta", price="3.950 TL"),
        Product(name="Taba Tote Çanta", price="3.950 TL"),
        Product(name="Taba Cüzdan", price="1.250 TL"),
        Product(name="Siyah Cüzdan", price="1.250 TL"),
        Product(name="Kahve Kemer", price="890 TL"),
        Product(name="Yeşil Kartlık", price="550 TL"),
    ],
    banned_words=["ucuz", "imitasyon"],
    brand_hashtag="lalederi",
    cta="whatsapp",
    whatsapp="0555 123 45 67",
    address="Serdivan, Sakarya",
    rhythm=Rhythm(posts_per_week=3, reels_per_week=2, stories_per_day=1),
    goals=["satis", "bilinirlik"],
)


def _demo_dir() -> Path:
    return Path(str(resources.files("tellal") / "demo_media"))


def import_demo_media(store: Store, media_dir: Path) -> list[int]:
    src = _demo_dir()
    manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    media_dir.mkdir(parents=True, exist_ok=True)
    ids = []
    base = time.time() - 50 * 86400
    for i, m in enumerate(manifest):
        mid = store.add_media(
            kind=m["kind"],
            filename="",
            mime="image/jpeg" if m["kind"] == "image" else "video/mp4",
            width=m["width"],
            height=m["height"],
            duration=m.get("duration"),
            size=(src / m["file"]).stat().st_size,
            title=m["title"],
            notes=m["notes"],
            tags=m["tags"],
        )
        name = f"{mid}{Path(m['file']).suffix}"
        shutil.copyfile(src / m["file"], media_dir / name)
        store.update_media(mid, filename=name, created=base + i * 3600)
        ids.append(mid)
    return ids


def seed(
    store: Store, media_dir: Path, tz_name: str = "Europe/Istanbul", weeks: int = 6, now: float | None = None
) -> dict[str, Any]:
    if store.get("seeded"):
        return {"seeded": False}
    now = now or time.time()
    save_brand(store, BRAND)
    acc = store.upsert_account(
        "demo",
        "demo-1",
        username="lale.deri",
        name="Lale Deri Atölyesi",
        followers=FOLLOWERS,
        picture="",
        token="demo",
        token_expires=now + 60 * 86400,
    )
    import_demo_media(store, media_dir)
    media = store.media_list()
    images = [m for m in media if m["kind"] == "image"]
    videos = [m for m in media if m["kind"] == "video"]
    rng = random.Random(7)
    prov = DemoProvider(tz_name)
    zone = tz(tz_name)
    today = datetime.fromtimestamp(now, zone).replace(hour=0, minute=0, second=0, microsecond=0)

    # Six weeks of history, with an uneven mix so the analysis has something to say.
    plan = [("post", 1, 12), ("reel", 2, 20), ("carousel", 3, 13), ("post", 4, 9), ("reel", 5, 21), ("post", 6, 19)]
    pillars = ["urun", "surec", "ipucu", "urun", "topluluk", "kanit", "urun", "surec"]
    pi = 0
    for w in range(weeks, 0, -1):
        for fmt, wd_off, hour in plan:
            day = today - timedelta(days=w * 7 - wd_off)
            h = hour + rng.choice([-1, 0, 0, 1])
            ts = at(day, max(8, min(22, h)), rng.choice([0, 10, 20, 30, 40]))
            if ts >= now - 3600:
                continue
            if fmt == "reel":
                ms = [rng.choice(videos)]
            elif fmt == "carousel":
                ms = rng.sample(images, 3)
            else:
                ms = [rng.choice(images)]
            pillar = "surec" if "surec" in (ms[0].get("tags") or []) else pillars[pi % len(pillars)]
            pi += 1
            if pillar == "kanit":
                pillar = "urun"
            d = content.generate(BRAND, ms, fmt, pillar, seed=pi)
            store.add_post(
                account_id=acc,
                format=fmt,
                media_ids=[m["id"] for m in ms],
                caption=d.caption,
                hashtags=d.hashtags,
                alt_text=d.alt_text,
                lang="tr",
                status="published",
                scheduled_at=ts,
                published_at=ts,
                remote_id=f"demo_hist_{pi}",
                source="plan",
                pillar=pillar,
                rationale=d.rationale,
                extra={"reel_script": d.reel_script, "carousel_slides": d.carousel_slides},
            )
        for k in range(7):
            day = today - timedelta(days=w * 7 - k)
            ts = at(day, 10, 15)
            if ts < now - 3600 and rng.random() < 0.7:
                m = rng.choice(images)
                d = content.generate(BRAND, [m], "story", "urun", seed=k + w * 10)
                store.add_post(
                    account_id=acc,
                    format="story",
                    media_ids=[m["id"]],
                    story_text="\n".join(d.story_frames),
                    lang="tr",
                    status="published",
                    scheduled_at=ts,
                    published_at=ts,
                    remote_id=f"demo_story_{w}_{k}",
                    source="plan",
                    pillar="urun",
                    extra={"story_frames": d.story_frames},
                )
    account = store.account(acc) or {}
    for p in store.posts(status="published"):
        store.save_insights(p["id"], **prov.simulate(p, FOLLOWERS, now))
    # Comments on the last week's posts
    for p in store.posts(status="published", since=now - 8 * 86400):
        if p["format"] == "story":
            continue
        for c in prov.comments(account, p["remote_id"], p["published_at"], count=rng.randint(1, 3)):
            if c["ts"] > now:
                continue
            intent = inbox.classify(c["text"])
            cid = store.add_comment(
                post_id=p["id"],
                remote_id=c["remote_id"],
                username=c["username"],
                text=c["text"],
                ts=c["ts"],
                intent=intent,
                status="spam" if intent == "spam" else "open",
            )
            if cid:
                store.update_comment(cid, reply_draft=inbox.draft_reply({**c, "intent": intent}, BRAND, p))
    store.put("last_refresh", {"insights": now, "comments": now, "tokens": now})

    # Next week, waiting for approval; and one approved post for later today so the scheduler has work.
    result = plan_week(store, BRAND, tz_name, start=today + timedelta(days=1), seed=11)
    m = images[0]
    d = content.generate(BRAND, [m], "post", "ipucu", seed=99)
    later = max(now + 2 * 3600, at(today, 20, 0))
    store.add_post(
        account_id=acc,
        format="post",
        media_ids=[m["id"]],
        caption=d.caption,
        hashtags=d.hashtags,
        alt_text=d.alt_text,
        lang="tr",
        status="approved",
        scheduled_at=later,
        source="plan",
        pillar="ipucu",
        rationale=d.rationale,
    )
    store.put("seeded", True)
    store.log("demo", "Demo hesap hazırlandı: Lale Deri Atölyesi (uydurma bir işletme).")
    return {"seeded": True, "planned": len(result["created"])}
