"""Builds a week of content: which day and hour, which format, which topic, which photo or video.

Every planned item lands in the approval queue ("pending"); nothing is published until the owner
approves it. Each item carries the reasons behind it, so the owner can see why it was planned that way.
"""

from __future__ import annotations

import random
import time
from datetime import datetime, timedelta
from typing import Any

from . import analytics, content
from .brand import Brand
from .clock import at, local, tz
from .db import Store

GOAL_MIX = {
    "satis": {"urun": 3, "surec": 1, "ipucu": 1, "topluluk": 1},
    "bilinirlik": {"surec": 2, "ipucu": 2, "urun": 2, "topluluk": 1},
    "topluluk": {"topluluk": 2, "surec": 1, "ipucu": 1, "urun": 1},
}
DAY_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
DAY_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
STORY_HOURS = [10, 17, 13, 19, 11, 21]


def _spread(n: int, days: int = 7, offset: int = 0) -> list[int]:
    """n days spread across the week, e.g. 3 -> Mon, Wed, Fri (shifted by offset)."""
    if n <= 0:
        return []
    out = []
    for i in range(n):
        out.append((offset + round(i * days / n)) % days)
    return out


def _pillar_bag(brand: Brand, by_pillar: dict[str, dict[str, float]], n: int, rng: random.Random) -> list[str]:
    weights: dict[str, float] = {}
    for g in brand.goals or ["satis"]:
        for k, v in GOAL_MIX[g].items():
            weights[k] = weights.get(k, 0) + v
    if by_pillar:
        best = max(by_pillar.items(), key=lambda kv: kv[1]["score"])[0]
        if best in weights:
            weights[best] += 1.5
    bag: list[str] = []
    while len(bag) < n:
        keys = list(weights)
        bag.append(rng.choices(keys, weights=[weights[k] for k in keys])[0])
    # avoid the same topic twice in a row
    for i in range(1, len(bag)):
        if bag[i] == bag[i - 1]:
            for j in range(i + 1, len(bag)):
                if bag[j] != bag[i]:
                    bag[i], bag[j] = bag[j], bag[i]
                    break
    return bag


class MediaPicker:
    """Least-used first, and not the same item twice in one plan."""

    def __init__(self, store: Store, rng: random.Random):
        self.items = store.media_list()
        self.usage = store.media_usage()
        self.taken: set[int] = set()
        self.rng = rng

    def _pool(self, kind: str) -> list[dict[str, Any]]:
        pool = [m for m in self.items if m["kind"] == kind and m["id"] not in self.taken and not m.get("parent_id")]
        self.rng.shuffle(pool)
        pool.sort(key=lambda m: self.usage.get(m["id"], 0))
        return pool

    def has(self, kind: str, n: int = 1) -> bool:
        return len(self._pool(kind)) >= n

    def take(self, kind: str, n: int = 1, vertical: bool = False) -> list[dict[str, Any]]:
        pool = self._pool(kind)
        if vertical:
            pool.sort(
                key=lambda m: (
                    self.usage.get(m["id"], 0),
                    0 if m.get("width") and m.get("height") and m["width"] / m["height"] < 0.7 else 1,
                )
            )
        if n > 1 and pool:
            # Prefer items that belong together (same title or a shared tag) for a carousel.
            first = pool[0]
            same = [
                m
                for m in pool[1:]
                if (m.get("title") and m.get("title") == first.get("title"))
                or set(m.get("tags") or []) & set(first.get("tags") or [])
            ]
            pool = [first, *same, *[m for m in pool[1:] if m not in same]]
        picked = pool[:n]
        for m in picked:
            self.taken.add(m["id"])
        return picked


def plan_week(
    store: Store,
    brand: Brand,
    tz_name: str,
    start: datetime | None = None,
    chat=None,  # noqa: ANN001
    lang: str = "tr",
    seed: int | None = None,
) -> dict[str, Any]:
    """Fills the 7 days starting at `start` (local midnight; default: tomorrow) up to the brand's rhythm."""
    zone = tz(tz_name)
    now = time.time()
    if start is None:
        start = (datetime.now(zone) + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    rng = random.Random(seed if seed is not None else int(start.timestamp()))
    posts = store.posts()
    existing = [
        p
        for p in posts
        if p["status"] not in {"rejected", "failed"}
        and p.get("scheduled_at")
        and start.timestamp() <= p["scheduled_at"] < end.timestamp()
    ]
    have = {f: sum(1 for p in existing if p["format"] == f) for f in content.FORMATS}
    r = brand.rhythm
    need_feed = max(0, r.posts_per_week - have["post"] - have["carousel"])
    need_reel = max(0, r.reels_per_week - have["reel"])
    need_story = max(0, r.stories_per_day * 7 - have["story"])

    summ = analytics.summary(posts, tz_name, days=60, now=now, lang=lang)
    slots = summ["best_slots"]
    learned = summ["learned"]
    picker = MediaPicker(store, rng)
    notes: list[str] = []
    tr = lang == "tr"

    # Not enough videos: turn missing Reels into photo posts and say so.
    videos = len(picker._pool("video"))
    if need_reel > videos:
        notes.append(
            (
                f"Reels için {need_reel} video gerekiyordu, kütüphanede {videos} kullanılabilir video var. Eksikler fotoğraf gönderisine çevrildi; "
                "Reels erişimi genelde daha yüksek, kısa dikey videolar ekleyin."
            )
            if tr
            else (
                f"Needed {need_reel} videos for Reels, found {videos}. The rest became photo posts; Reels usually reach more people, add short vertical videos."
            )
        )
        need_feed += need_reel - videos
        need_reel = videos

    occasions = content.upcoming_occasions(start.date(), horizon_days=10)
    slots_used: set[tuple[int, int]] = {
        (local(p["scheduled_at"], tz_name).weekday(), local(p["scheduled_at"], tz_name).hour) for p in existing
    }
    jobs: list[tuple[str, int, int]] = []  # (format, day offset, hour)
    feed_days = _spread(need_feed, offset=0)
    reel_days = _spread(need_reel, offset=1)
    for d in feed_days:
        jobs.append(("post", d, 0))
    for d in reel_days:
        jobs.append(("reel", d, 1))
    for d in range(7):
        for k in range(r.stories_per_day):
            if len([j for j in jobs if j[0] == "story"]) < need_story:
                jobs.append(("story", d, 100 + k))

    pillars = _pillar_bag(brand, summ["by_pillar"], len([j for j in jobs if j[0] != "story"]), rng)
    created: list[int] = []
    feed_count = 0
    reels_done = 0
    for fmt, d, which in sorted(jobs, key=lambda j: (j[1], j[2])):
        day = start + timedelta(days=d)
        wd = day.weekday()
        if fmt == "story":
            h = STORY_HOURS[(which - 100) % len(STORY_HOURS)]
            reason_time = (
                "Hikâyeler sabah ve öğleden sonra, gönderilerle çakışmayacak saatte."
                if tr
                else "Stories go out at a time that doesn't clash with posts."
            )
        else:
            hours = slots.get(wd, analytics.DEFAULT_SLOTS[wd])
            h = hours[min(which, len(hours) - 1)]
            if (wd, h) in slots_used:
                h = hours[1 - min(which, 1)] if len(hours) > 1 else h + 2
            reason_time = (
                (
                    f"{DAY_TR[wd]} {h}:00: geçmiş paylaşımlarınızda bu saatlerde etkileşim en yüksek."
                    if learned
                    else f"{DAY_TR[wd]} {h}:00: Türkiye'de öğle arası ve akşam saatleri en yoğun dönem; veriniz biriktikçe saatler size göre ayarlanacak."
                )
                if tr
                else (
                    f"{DAY_EN[wd]} {h}:00: your past posts did best around this time."
                    if learned
                    else f"{DAY_EN[wd]} {h}:00: lunch and evening are the busiest hours; times adapt as your data grows."
                )
            )
        slots_used.add((wd, h))
        minute = rng.choice([0, 5, 10, 15, 20, 30, 40, 45])
        when = at(day, h, minute)
        if when < now + 600:
            continue

        actual = fmt
        if fmt == "reel":
            reels_done += 1
            media = picker.take("video", 1, vertical=True)
            if not media:
                actual, media = "post", picker.take("image", 1)
        elif fmt == "story":
            # Videos are kept for Reels; a story only gets one when there are spares.
            reels_left = sum(1 for j in jobs if j[0] == "reel") - reels_done
            spare = len(picker._pool("video")) > reels_left
            kind = "video" if spare and rng.random() < 0.3 else "image"
            media = picker.take(kind, 1, vertical=True) or picker.take("image", 1)
            if not media:
                # Stories may reuse library items; reset the picker's memory for them.
                media = [m for m in picker.items if m["kind"] == "image"][:1]
        else:
            feed_count += 1
            if feed_count % 3 == 0 and picker.has("image", 3):
                actual = "carousel"
                media = picker.take("image", min(4, len(picker._pool("image"))))
            else:
                media = picker.take("image", 1)
        if not media:
            notes.append(
                "Kütüphanede yeterli fotoğraf yok; bazı günler boş kaldı."
                if tr
                else "Not enough photos in the library; some days are empty."
            )
            continue

        pillar = "urun" if actual == "story" else pillars.pop(0) if pillars else "urun"
        occasion = None
        for o in occasions:
            od = datetime.fromisoformat(o["date"]).date()
            if 0 <= (od - day.date()).days <= 3 and actual != "story":
                occasion = o["name"]
                if pillar == "urun":
                    pillar = "kampanya"
                break
        s = rng.randint(0, 10_000)
        if chat:
            draft = content.llm_generate(
                brand, media, actual, pillar, brand.primary_lang, occasion, s, False, brand.ai_label_default, chat
            )
        else:
            draft = content.generate(
                brand, media, actual, pillar, brand.primary_lang, occasion, s, False, brand.ai_label_default
            )
        rationale = [reason_time]
        if actual == "carousel":
            rationale.append(
                "Kaydırmalı gönderi: birden fazla kare izlenme süresini uzatır ve kaydırmayan kişiye ikinci karesi tekrar gösterilebilir."
                if tr
                else "Carousel: several slides keep people longer, and Instagram may show the second slide to people who skipped it."
            )
        if occasion:
            rationale.append(f"Yaklaşan özel gün: {occasion}." if tr else f"Upcoming occasion: {occasion}.")
        rationale += draft.rationale
        pid = store.add_post(
            account_id=None,
            format=actual,
            media_ids=[m["id"] for m in media],
            caption=draft.caption,
            hashtags=draft.hashtags,
            alt_text=draft.alt_text,
            story_text="\n".join(draft.story_frames),
            reel_hook=draft.reel_hook,
            lang=draft.lang,
            ai_label=brand.ai_label_default,
            sponsored=False,
            status="pending",
            scheduled_at=when,
            source="plan",
            rationale=rationale,
            pillar=pillar,
            extra={
                "story_frames": draft.story_frames,
                "sticker": draft.sticker,
                "reel_script": draft.reel_script,
                "carousel_slides": draft.carousel_slides,
                "engine": draft.engine,
                "seed": s,
                "occasion": occasion,
            },
        )
        created.append(pid)
    if created:
        store.log(
            "plan",
            (
                f"{len(created)} içerik planlandı, onayınızı bekliyor."
                if tr
                else f"Planned {len(created)} items, waiting for approval."
            ),
        )
    return {
        "created": created,
        "notes": list(dict.fromkeys(notes)),
        "start": start.isoformat(),
        "learned": learned,
        "occasions": occasions,
    }


def regenerate(
    store: Store,
    brand: Brand,
    post_id: int,
    chat=None,
    pillar: str | None = None,
    fmt: str | None = None,  # noqa: ANN001
    lang: str | None = None,
) -> dict[str, Any] | None:
    p = store.post(post_id)
    if not p or p["status"] in {"published", "publishing"}:
        return None
    media = [m for m in (store.media(i) for i in p["media_ids"]) if m]
    seed = int((p.get("extra") or {}).get("seed", 0)) + 1
    pillar = pillar or p.get("pillar") or "urun"
    fmt = fmt or p["format"]
    lang = lang or p.get("lang") or brand.primary_lang
    occ = (p.get("extra") or {}).get("occasion")
    if chat:
        d = content.llm_generate(brand, media, fmt, pillar, lang, occ, seed, p["sponsored"], p["ai_label"], chat)
    else:
        d = content.generate(brand, media, fmt, pillar, lang, occ, seed, p["sponsored"], p["ai_label"])
    extra = {
        **(p.get("extra") or {}),
        "story_frames": d.story_frames,
        "sticker": d.sticker,
        "reel_script": d.reel_script,
        "carousel_slides": d.carousel_slides,
        "engine": d.engine,
        "seed": seed,
    }
    keep = [x for x in (p.get("rationale") or []) if ":00" in x][:1]
    store.update_post(
        post_id,
        caption=d.caption,
        hashtags=d.hashtags,
        alt_text=d.alt_text,
        story_text="\n".join(d.story_frames),
        reel_hook=d.reel_hook,
        pillar=pillar,
        format=fmt,
        lang=d.lang,
        extra=extra,
        rationale=keep + d.rationale,
        status="pending" if p["status"] in {"approved", "rejected", "failed"} else p["status"],
    )
    return store.post(post_id)
