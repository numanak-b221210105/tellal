"""Ad suggestions: which post to boost, with what budget, for how long, and what to expect.

Tellal never spends money. It points at posts that already did well organically (boosting a proven post
is the cheapest way to buy reach), and gives honest ranges, not promises. Cost ranges are Turkish
market CPMs (cost per 1000 impressions) for small local campaigns in 2026; they move with season and
competition (November and December are the most expensive months).
"""

from __future__ import annotations

import statistics
import time
from typing import Any

from .analytics import rates
from .brand import SECTORS, Brand

CPM_TRY = {"reel": (18.0, 50.0), "story": (20.0, 45.0), "post": (30.0, 70.0), "carousel": (30.0, 70.0)}
PEAK_MONTHS = {11, 12}
LOCATION_FEE = 0.05  # Meta's location-based fee for ads served in Turkey (since 1 July 2026)
FREQUENCY = 1.7  # average times one person sees the ad in a short campaign
TIERS = [("deneme", 100, 3), ("dengeli", 200, 5), ("guclu", 400, 7)]
TIER_NAMES = {
    "tr": {"deneme": "Deneme", "dengeli": "Dengeli", "guclu": "Güçlü"},
    "en": {"deneme": "Test", "dengeli": "Balanced", "guclu": "Strong"},
}


def estimate(fmt: str, daily_try: float, days: int, month: int | None = None) -> dict[str, Any]:
    lo, hi = CPM_TRY.get(fmt, CPM_TRY["post"])
    if (month or time.localtime().tm_mon) in PEAK_MONTHS:
        lo, hi = lo * 1.2, hi * 1.3
    spend = daily_try * days
    fee = spend * LOCATION_FEE
    imp = (spend / hi * 1000, spend / lo * 1000)
    reach = (imp[0] / FREQUENCY, imp[1] / FREQUENCY)
    return {
        "daily": daily_try,
        "days": days,
        "spend": round(spend),
        "fee": round(fee),
        "total": round(spend + fee),
        "cpm": [round(lo), round(hi)],
        "impressions": [int(round(imp[0], -2)), int(round(imp[1], -2))],
        "reach": [int(round(reach[0], -2)), int(round(reach[1], -2))],
    }


def _strength(p: dict[str, Any]) -> float:
    return rates(p)["score"] * ((p.get("reach") or 0) ** 0.5)


def candidates(
    posts: list[dict[str, Any]],
    brand: Brand,
    lang: str = "tr",
    now: float | None = None,
    days: int = 30,
    limit: int = 3,
) -> dict[str, Any]:
    now = now or time.time()
    tr = lang == "tr"
    pool = [
        p
        for p in posts
        if p.get("status") == "published"
        and p.get("reach")
        and p.get("format") != "story"
        and p.get("published_at", 0) >= now - days * 86400
        and now - p.get("published_at", now) >= 18 * 3600
    ]
    if len(pool) < 3:
        return {
            "items": [],
            "note": (
                "Öneri için son 30 günde en az 3 yayınlanmış gönderi gerekiyor (en az 18 saatlik)."
                if tr
                else "Needs at least 3 published posts from the last 30 days (18+ hours old)."
            ),
        }
    med = statistics.median(_strength(p) for p in pool) or 1e-9
    ranked = sorted(pool, key=_strength, reverse=True)
    month = time.localtime(now).tm_mon
    items = []
    seen_media: set[int] = set()
    for p in ranked:
        ratio = _strength(p) / med
        if ratio < 1.15 or len(items) >= limit:
            continue
        first = (p.get("media_ids") or [0])[0]
        if first in seen_media:  # one suggestion per photo or video
            continue
        seen_media.add(first)
        r = rates(p)
        why = []
        if r["send"] >= 0.006:
            why.append(
                f"erişim başına gönderilme %{r['send'] * 100:.1f}" if tr else f"sends per reach {r['send'] * 100:.1f}%"
            )
        if r["save"] >= 0.008:
            why.append(f"kaydetme %{r['save'] * 100:.1f}" if tr else f"saves {r['save'] * 100:.1f}%")
        why.append(f"ortalamanın {ratio:.1f} katı performans" if tr else f"{ratio:.1f}x your median")
        caption = p.get("caption") or ""
        risky = "[" in caption
        goal = (
            "messages"
            if brand.cta in {"dm", "whatsapp"}
            else "visits"
            if brand.cta == "visit"
            else "traffic"
            if brand.cta == "link"
            else "reach"
        )
        items.append(
            {
                "post_id": p["id"],
                "format": p["format"],
                "pillar": p.get("pillar"),
                "caption": caption[:120],
                "media_ids": p.get("media_ids"),
                "reach": p["reach"],
                "ratio": round(ratio, 2),
                "why": why,
                "goal": goal,
                "blocked": risky,
                "tiers": [
                    {"key": k, "name": TIER_NAMES["tr" if tr else "en"][k], **estimate(p["format"], d, n, month)}
                    for k, d, n in TIERS
                ],
            }
        )
    return {"items": items, "targeting": targeting(brand, lang), "notes": notes(lang, month)}


def targeting(b: Brand, lang: str = "tr") -> list[str]:
    tr = lang == "tr"
    tags = [str(t) for t in SECTORS.get(b.sector, SECTORS["diger"])["tags"]][:3]
    out = []
    if b.cta == "visit" and b.city:
        out.append(
            f"Konum: {b.city}, işletmenin çevresinde 5–15 km" if tr else f"Location: {b.city}, 5–15 km around the shop"
        )
    elif b.city:
        out.append(
            f"Konum: önce {b.city}, iyi giderse Türkiye geneli"
            if tr
            else f"Location: {b.city} first, then country-wide if it works"
        )
    out.append(
        (
            "Hedef kitle: Advantage+ (otomatik) kitle, öneri olarak: "
            if tr
            else "Audience: Advantage+ audience, with suggestions: "
        )
        + (b.audience or ", ".join(tags))
    )
    out.append(
        ("Amaç: " if tr else "Objective: ")
        + {
            "dm": "Mesajlar (Instagram DM)" if tr else "Messages (Instagram DM)",
            "whatsapp": "Mesajlar (WhatsApp)" if tr else "Messages (WhatsApp)",
            "link": "Trafik (web sitesi)" if tr else "Traffic (website)",
            "visit": "Erişim + mağaza ziyareti" if tr else "Reach + store visits",
            "call": "Aramalar" if tr else "Calls",
        }[b.cta]
    )
    return out


def notes(lang: str = "tr", month: int | None = None) -> list[str]:
    if lang == "tr":
        out = [
            "Tellal reklam vermez, para harcamaz: öneriyi Instagram'da gönderinin altındaki 'Öne çıkar' düğmesiyle ya da Meta Reklam Yöneticisi'nde uygularsınız.",
            "Tahminler aralıktır, garanti değildir. İlk 2 gün sonuçları izleyin; gönderilme ve mesaj gelmiyorsa durdurun.",
            "Meta, Türkiye'de gösterilen reklamlara 1 Temmuz 2026'dan beri %5 konum ücreti ekliyor (toplamda gösterildi).",
            "Meta faturası yurt dışından hizmet sayılır: KDV mükellefiyseniz %20 KDV'yi 2 No.lu KDV beyannamesiyle siz beyan eder, sonra indirebilirsiniz. Muhasebecinize danışın.",
            "Reklamda indirim duyuruyorsanız son 30 günün en düşük fiyatını ve kampanya tarihlerini belirtin.",
        ]
        if (month or 0) in PEAK_MONTHS:
            out.insert(
                2,
                "Kasım–Aralık reklamın en pahalı dönemi (Efsane Cuma, yılbaşı); maliyet aralıkları buna göre yükseltildi.",
            )
    else:
        out = [
            "Tellal never runs ads or spends money: apply the suggestion with 'Boost post' in Instagram or in Meta Ads Manager.",
            "Estimates are ranges, not guarantees. Watch the first 2 days and stop if there are no sends or messages.",
            "Meta adds a 5% location fee to ads shown in Turkey since 1 July 2026 (included in the total).",
            "Meta's invoice counts as an imported service: VAT-registered businesses declare 20% VAT via the No. 2 VAT return. Ask your accountant.",
        ]
        if (month or 0) in PEAK_MONTHS:
            out.insert(2, "November–December is the most expensive season; cost ranges are raised accordingly.")
    return out
