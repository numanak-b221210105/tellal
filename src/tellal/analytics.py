"""What worked and when: per-reach rates, format and topic comparison, best hours, weekly report.

Raw likes say little when reach differs, so everything is compared per reach. The score weights the
actions Instagram treats as strongest: a send (share) > a save > a comment > a like.
"""

from __future__ import annotations

import statistics
import time
from collections import defaultdict
from typing import Any

from .clock import local

WEIGHTS = {"shares": 3.0, "saves": 2.0, "comments": 1.5, "likes": 1.0}
DEFAULT_SLOTS = {  # weekday (0=Mon) -> good local hours, from general Turkish usage patterns
    0: [12, 20],
    1: [12, 20],
    2: [13, 21],
    3: [12, 20],
    4: [13, 21],
    5: [11, 20],
    6: [12, 21],
}
MIN_POSTS_FOR_LEARNING = 8
DAY_TR = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
DAY_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def rates(p: dict[str, Any]) -> dict[str, float]:
    reach = p.get("reach") or 0
    if reach <= 0:
        return {"engagement": 0.0, "send": 0.0, "save": 0.0, "like": 0.0, "comment": 0.0, "score": 0.0}
    g = lambda k: (p.get(k) or 0) / reach  # noqa: E731
    likes, comments = g("likes"), g("comment_count") if "comment_count" in p else g("comments")
    return {
        "engagement": likes + comments + g("saves") + g("shares"),
        "send": g("shares"),
        "save": g("saves"),
        "like": likes,
        "comment": comments,
        "score": WEIGHTS["shares"] * g("shares")
        + WEIGHTS["saves"] * g("saves")
        + WEIGHTS["comments"] * comments
        + likes,
    }


def _published(
    posts: list[dict[str, Any]], since: float | None = None, until: float | None = None
) -> list[dict[str, Any]]:
    out = []
    for p in posts:
        if p.get("status") != "published" or not p.get("published_at") or not p.get("reach"):
            continue
        if since and p["published_at"] < since:
            continue
        if until and p["published_at"] >= until:
            continue
        out.append(p)
    return out


def _avg(xs: list[float]) -> float:
    return statistics.fmean(xs) if xs else 0.0


def _group(posts: list[dict[str, Any]], key: str) -> dict[str, dict[str, float]]:
    g: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in posts:
        g[p.get(key) or "-"].append(p)
    return {
        k: {
            "count": len(v),
            "reach": _avg([x["reach"] for x in v]),
            "score": _avg([rates(x)["score"] for x in v]),
            "send": _avg([rates(x)["send"] for x in v]),
            "save": _avg([rates(x)["save"] for x in v]),
            "engagement": _avg([rates(x)["engagement"] for x in v]),
            "watch_s": _avg([x["avg_watch_ms"] / 1000 for x in v if x.get("avg_watch_ms")]),
        }
        for k, v in g.items()
    }


def heatmap(posts: list[dict[str, Any]], tz_name: str) -> list[list[float | None]]:
    """7x24 grid (weekday x hour) of the average reach-weighted score; None where there's no data."""
    cells: dict[tuple[int, int], list[float]] = defaultdict(list)
    for p in _published(posts):
        if p.get("format") == "story":
            continue
        d = local(p["published_at"], tz_name)
        # Reach and quality both matter for timing: score x log-ish reach.
        cells[(d.weekday(), d.hour)].append(rates(p)["score"] * (p["reach"] ** 0.5))
    return [[(_avg(cells[(w, h)]) if cells.get((w, h)) else None) for h in range(24)] for w in range(7)]


def best_slots(posts: list[dict[str, Any]], tz_name: str, quiet: tuple[int, int] = (23, 8)) -> dict[int, list[int]]:
    """Best two hours per weekday: learned when there's enough history, otherwise sensible defaults."""
    pub = [p for p in _published(posts) if p.get("format") != "story"]
    if len(pub) < MIN_POSTS_FOR_LEARNING:
        return DEFAULT_SLOTS
    grid = heatmap(posts, tz_name)
    # Smooth by hour across all days: one good Tuesday 20:00 suggests 20:00 is good in general.
    by_hour = [_avg([grid[w][h] for w in range(7) if grid[w][h] is not None]) for h in range(24)]
    a, b = quiet

    def ok(h: int) -> bool:
        return not ((a <= h or h < b) if a > b else (a <= h < b))

    out: dict[int, list[int]] = {}
    for w in range(7):
        scored = []
        for h in range(24):
            if not ok(h):
                continue
            own = grid[w][h]
            v = (0.6 * own + 0.4 * by_hour[h]) if own is not None else 0.8 * by_hour[h]
            # Default hours keep a small prior so the plan never jumps to a random empty slot.
            v += 0.05 * max(by_hour or [0]) if h in DEFAULT_SLOTS[w] else 0
            scored.append((v, h))
        scored.sort(reverse=True)
        picks: list[int] = []
        for _, h in scored:
            if all(abs(h - x) >= 3 for x in picks):
                picks.append(h)
            if len(picks) == 2:
                break
        out[w] = sorted(picks) or DEFAULT_SLOTS[w]
    return out


def series(
    cur: list[dict[str, Any]], prev: list[dict[str, Any]], tz_name: str, days: int, now: float
) -> dict[str, Any]:
    """Reach per local day for this period and the one before it, aligned day by day."""
    end = local(now, tz_name).date()
    labels = [(end.toordinal() - days + 1 + i) for i in range(days)]
    cur_by: dict[int, int] = defaultdict(int)
    prev_by: dict[int, int] = defaultdict(int)
    lo, hi = labels[0], labels[-1]
    # The period is "the last N x 24 hours", so its first post can fall on the day before the first label.
    for p in cur:
        cur_by[min(hi, max(lo, local(p["published_at"], tz_name).date().toordinal()))] += p.get("reach") or 0
    for p in prev:
        prev_by[min(hi, max(lo, local(p["published_at"], tz_name).date().toordinal() + days))] += p.get("reach") or 0
    from datetime import date

    return {
        "labels": [date.fromordinal(o).isoformat() for o in labels],
        "current": [cur_by.get(o, 0) for o in labels],
        "previous": [prev_by.get(o, 0) for o in labels],
    }


def summary(
    posts: list[dict[str, Any]], tz_name: str, days: int = 30, now: float | None = None, lang: str = "tr"
) -> dict[str, Any]:
    now = now or time.time()
    since = now - days * 86400
    cur = _published(posts, since, now)
    prev = _published(posts, since - days * 86400, since)

    def totals(ps: list[dict[str, Any]]) -> dict[str, float]:
        t = {
            k: sum(p.get(k) or 0 for p in ps)
            for k in ["reach", "views", "likes", "saves", "shares", "follows", "profile_visits"]
        }
        t["comments"] = sum(p.get("comment_count") or 0 for p in ps)
        t["posts"] = len(ps)
        t["avg_reach"] = t["reach"] / len(ps) if ps else 0
        t["score"] = _avg([rates(p)["score"] for p in ps])
        return t

    tc, tp = totals(cur), totals(prev)
    change = {k: ((tc[k] - tp[k]) / tp[k] if tp.get(k) else None) for k in tc}
    ranked = sorted(cur, key=lambda p: rates(p)["score"] * (p["reach"] ** 0.5), reverse=True)

    def slim(p: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": p["id"],
            "format": p["format"],
            "pillar": p.get("pillar"),
            "caption": (p.get("caption") or "")[:90],
            "reach": p["reach"],
            "published_at": p["published_at"],
            "media_ids": p.get("media_ids"),
            **{k: round(v, 4) for k, v in rates(p).items()},
        }

    by_format, by_pillar = _group(cur, "format"), _group(cur, "pillar")
    slots = best_slots(posts, tz_name)
    return {
        "series": series(cur, prev, tz_name, days, now),
        "posts": [slim(p) for p in sorted(cur, key=lambda p: p["published_at"], reverse=True)],
        "days": days,
        "totals": tc,
        "previous": tp,
        "change": change,
        "by_format": by_format,
        "by_pillar": by_pillar,
        "heatmap": heatmap(cur or posts, tz_name),
        "best_slots": slots,
        "learned": len([p for p in _published(posts) if p.get("format") != "story"]) >= MIN_POSTS_FOR_LEARNING,
        "top": [slim(p) for p in ranked[:5]],
        "bottom": [slim(p) for p in ranked[-3:]] if len(ranked) > 5 else [],
        "advice": advice(cur, by_format, by_pillar, slots, lang),
    }


PILLAR_NAMES = {
    "tr": {
        "urun": "ürün tanıtımı",
        "surec": "kamera arkası",
        "ipucu": "ipucu/rehber",
        "topluluk": "soru/anket",
        "kampanya": "kampanya",
        "kanit": "müşteri yorumu",
    },
    "en": {
        "urun": "product",
        "surec": "behind the scenes",
        "ipucu": "tips",
        "topluluk": "questions",
        "kampanya": "offers",
        "kanit": "reviews",
    },
}


def advice(
    cur: list[dict[str, Any]], by_format: dict, by_pillar: dict, slots: dict[int, list[int]], lang: str
) -> list[str]:
    tr = lang == "tr"
    names = PILLAR_NAMES["tr" if tr else "en"]
    out: list[str] = []
    if len(cur) < 4:
        out.append(
            "Yorum yapmak için henüz az veri var; birkaç hafta düzenli paylaşınca öneriler netleşir."
            if tr
            else "Not enough data yet; a few weeks of regular posting will sharpen the advice."
        )
        return out
    reel, post = by_format.get("reel"), by_format.get("post") or by_format.get("carousel")
    if reel and post and post["reach"]:
        x = reel["reach"] / post["reach"]
        if x >= 1.3:
            out.append(
                f"Reels ortalama {x:.1f} kat daha fazla kişiye ulaşıyor: yeni kitleye ulaşmak için Reels oranını artırın."
                if tr
                else f"Reels reach {x:.1f}x more people: post more Reels to reach new people."
            )
        elif x < 0.9:
            out.append(
                "Reels beklenenden az erişiyor: ilk 2 saniyeyi güçlendirin, videoyu 7–15 saniyeye indirin."
                if tr
                else "Reels underperform: open stronger in the first 2 seconds and cut to 7–15 seconds."
            )
    if reel and reel.get("watch_s"):
        out.append(
            (
                f"Reels ortalama izlenme süresi {reel['watch_s']:.1f} sn. "
                if tr
                else f"Average Reel watch time is {reel['watch_s']:.1f} s. "
            )
            + (
                "Videolarınızı bu sürenin biraz üstünde tutun; sonuna kadar izlenme erişimi artırır."
                if tr
                else "Keep videos close to that length; finished views lift reach."
            )
        )
    if len(by_pillar) >= 2:
        best = max(by_pillar.items(), key=lambda kv: kv[1]["score"])
        worst = min(by_pillar.items(), key=lambda kv: kv[1]["score"])
        if best[0] != worst[0] and best[1]["count"] >= 2:
            out.append(
                f"En çok etkileşim alan konu: {names.get(best[0], best[0])}. Bundan haftada bir fazlası planlandı."
                if tr
                else f"Best topic: {names.get(best[0], best[0])}. The plan adds one more per week."
            )
        save_best = max(by_pillar.items(), key=lambda kv: kv[1]["save"])
        if save_best[1]["save"] > 0.01:
            out.append(
                f"'{names.get(save_best[0], save_best[0])}' içerikleri kaydediliyor: kaydetme, Instagram'a 'tekrar dönülecek içerik' sinyali verir."
                if tr
                else f"'{names.get(save_best[0], save_best[0])}' posts get saved, which tells Instagram they're worth returning to."
            )
    sends = _avg([rates(p)["send"] for p in cur])
    if sends < 0.004:
        out.append(
            "Gönderilme (paylaşma) oranı düşük. Açıklamaları 'bunu birine gönderin' daveti ile bitirmek ve hediye fikri gibi paylaşılabilir içerik denemek işe yarar."
            if tr
            else "Few sends. End captions by inviting people to send the post, and try shareable ideas such as gift guides."
        )
    h = slots.get(4, [20])
    out.append(
        (
            f"Hafta içi en iyi saatleriniz: {', '.join(f'{x}:00' for x in sorted({x for v in list(slots.values())[:5] for x in v}))}."
            if tr
            else f"Best weekday hours: {', '.join(f'{x}:00' for x in sorted({x for v in list(slots.values())[:5] for x in v}))}."
        )
        if h
        else ""
    )
    return [x for x in out if x]
