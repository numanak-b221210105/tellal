"""Checks a post before it can be approved: Instagram's technical limits and Turkish advertising rules.

Each finding has a level:
- "error": publishing is blocked until it is fixed;
- "warn": allowed, but the owner should look at it;
- "info": a tip.

The Turkish rules come from the Ticari Reklam ve Haksız Ticari Uygulamalar Yönetmeliği (amended, in force
from 1 August 2026) and the Ticaret Bakanlığı influencer guide. This is a checklist, not legal advice.
"""

from __future__ import annotations

import re
from typing import Any

from .brand import Brand
from .content import MAX_HASHTAGS, placeholders

CAPTION_MAX = 2200
FEED_RATIO = (0.8, 1.91)  # 4:5 portrait to 1.91:1 landscape
VERTICAL_RATIO = (0.5, 0.6)  # around 9:16 (0.5625)
REEL_SECONDS = (3, 900)
STORY_VIDEO_SECONDS = (3, 60)
CAROUSEL_ITEMS = (2, 10)
IMAGE_MAX_BYTES = 8 * 1024 * 1024

DISCOUNT = re.compile(
    r"(%\s?\d{1,2}|\d{1,2}\s?%|indirim|kampanya|fırsat|discount|\bsale\b|popust|reducere|akcija)", re.I
)
AD_TAGS = re.compile(
    r"#(reklam|işbirliği|isbirligi|iş_birliği|tanıtım|ad|sponsored|reklama|oglas|reclama)\b|\b(reklam|iş birliği|tanıtım)\b",
    re.I,
)
SUPERLATIVE = re.compile(
    r"\b(en iyi|en ucuz|en kaliteli|bir numara|tek adres|rakipsiz|türkiye'nin en|dünyanın en|best in|number one|#1|cheapest)\b",
    re.I,
)
HEALTH = re.compile(
    r"\b(tedavi eder|iyileştirir|şifa|zayıflatır|kilo verdirir|kanser|bağışıklığı güçlendirir|cures?|heals?|weight loss|detoks)\b",
    re.I,
)
GUARANTEE = re.compile(r"\b(garantili|%100 garanti|kesin sonuç|guaranteed)\b", re.I)
URL = re.compile(r"(https?://|www\.)\S+", re.I)
HASHTAG = re.compile(r"(?<!\S)#(\w+)", re.U)

M = {
    "caption_long": (
        "Açıklama {n} karakter; Instagram en fazla 2200'e izin verir.",
        "Caption is {n} characters; Instagram allows at most 2200.",
    ),
    "too_many_tags": (
        "Toplam {n} hashtag var (açıklama + etiket listesi + ilk yorum). Instagram en fazla 5'e izin veriyor.",
        "{n} hashtags in total (caption + tag list + first comment). Instagram allows at most 5.",
    ),
    "no_media": ("Medya seçilmedi.", "No media selected."),
    "media_missing": (
        "Seçilen medyalardan biri kütüphanede yok.",
        "One of the selected media items is missing from the library.",
    ),
    "carousel_count": (
        "Kaydırmalı gönderi 2 ile 10 arasında öğe ister; şu an {n}.",
        "A carousel needs 2 to 10 items; it has {n}.",
    ),
    "reel_needs_video": ("Reels için video gerekir.", "A Reel needs a video."),
    "post_needs_image": (
        "Tek gönderi için bir fotoğraf seçin (video paylaşmak için Reels kullanın).",
        "Choose a photo for a single post (use a Reel for video).",
    ),
    "feed_ratio": (
        "'{t}' oranı {r}; akışta 4:5 ile 1.91:1 arası kabul edilir. Kırpma aracıyla 4:5 yapın.",
        "'{t}' has ratio {r}; the feed accepts 4:5 to 1.91:1. Crop it to 4:5.",
    ),
    "vertical_ratio": (
        "'{t}' dikey (9:16) değil; {f} için kenarlarda boşluk ya da kırpılma olur.",
        "'{t}' is not vertical (9:16); a {f} will be letterboxed or cropped.",
    ),
    "reel_len": ("Video {s} sn; Reels 3 sn ile 15 dk arası olmalı.", "Video is {s} s; Reels must be 3 s to 15 min."),
    "reel_long": (
        "Video {s} sn. 90 saniyeden uzun Reels daha az izleyiciye önerilir; 7–30 sn deneyin.",
        "Video is {s} s. Reels over 90 s are recommended to fewer people; try 7–30 s.",
    ),
    "story_len": ("Hikâye videosu {s} sn; 3–60 sn arası olmalı.", "Story video is {s} s; it must be 3–60 s."),
    "image_big": (
        "'{t}' 8 MB'tan büyük; Instagram reddeder. Uygulama küçültebilir.",
        "'{t}' is larger than 8 MB; Instagram will reject it.",
    ),
    "image_format": (
        "'{t}' JPEG değil; Instagram yalnızca JPEG kabul eder, yükleme sırasında dönüştürülür.",
        "'{t}' is not JPEG; Instagram only accepts JPEG. It is converted on upload.",
    ),
    "placeholder": (
        "Doldurulmamış alan var: {p}. Gerçek bilgiyle değiştirin ya da silin.",
        "Unfilled placeholder: {p}. Replace it with real information or remove it.",
    ),
    "banned": ("Marka için yasaklı kelime: '{w}'.", "Word banned by the brand: '{w}'."),
    "sponsored_tag": (
        "Bu bir iş birliği/reklam olarak işaretli ama açıklamanın başında '#reklam', 'iş birliği' ya da 'tanıtım' ibaresi yok. Yönetmelik bunu açıkça istiyor.",
        "Marked as sponsored but the caption has no clear '#ad' / 'paid partnership' disclosure.",
    ),
    "sponsored_early": (
        "Reklam ibaresi açıklamanın sonunda kalmış; 'devamı'na basmadan görünecek şekilde ilk satırlara taşıyın.",
        "The ad disclosure is at the end; move it up so it shows before 'more'.",
    ),
    "ai_label": (
        "Yapay zekâ ile üretilmiş görsel içerik işaretli: Instagram'da 'Yapay zekâ bilgisi' etiketi açılacak ve açıklamaya not eklenmeli.",
        "AI-generated visuals: the Instagram 'AI info' label will be set and the caption should say so.",
    ),
    "ai_label_text": (
        "Yapay zekâ içeriği işaretli ama açıklamada bunu belirten bir not yok.",
        "Marked as AI-generated but the caption does not say so.",
    ),
    "discount": (
        "İndirim/kampanya ifadesi var. İndirimli fiyat duyurusunda son 30 gündeki en düşük fiyat da belirtilmeli, kampanya süresi ve koşulları açık olmalı.",
        "Mentions a discount. Show the lowest price of the last 30 days and the offer's dates and terms.",
    ),
    "superlative": (
        "'{w}' gibi üstünlük iddiaları belgelenemezse yanıltıcı reklam sayılabilir.",
        "Claims like '{w}' can count as misleading unless you can prove them.",
    ),
    "health": (
        "'{w}': sağlık/iyileştirme iddiası. Gıda, kozmetik ve takviyelerde bu tür ifadeler yasak ya da izne tabi.",
        "'{w}': a health claim. These are banned or need approval for food, cosmetics and supplements.",
    ),
    "guarantee": (
        "'{w}': kesin sonuç vaadi tüketiciyi yanıltıcı sayılabilir.",
        "'{w}': a guaranteed result can be misleading.",
    ),
    "url": (
        "Açıklamadaki linkler tıklanamaz; 'biyografideki link' deyin.",
        "Links in captions aren't clickable; point to the link in bio.",
    ),
    "hook_long": (
        "İlk satır {n} karakter; ilk ~125 karakter 'devamı'ndan önce görünür, kancayı kısaltın.",
        "First line is {n} characters; only ~125 show before 'more'.",
    ),
    "no_alt": (
        "Alternatif metin yok; görme engelli kullanıcılar ve arama için ekleyin.",
        "No alt text; add it for screen readers and search.",
    ),
    "empty_caption": ("Açıklama boş.", "Caption is empty."),
    "story_no_link": (
        "Hikâyelerde link, anket ve soru çıkartmalarını API ekleyemez; paylaşımdan sonra uygulamadan ekleyin.",
        "The API can't add link, poll or question stickers to Stories; add them in the app after posting.",
    ),
    "no_account": (
        "Bağlı hesap yok; gönderi yalnızca taslak olarak kalabilir.",
        "No connected account; the post can only stay a draft.",
    ),
    "quiet_hours": (
        "Planlanan saat markanın sessiz saatlerinde ({a}:00–{b}:00).",
        "Scheduled inside the brand's quiet hours ({a}:00–{b}:00).",
    ),
    "past": (
        "Planlanan zaman geçmişte; onaylanırsa hemen paylaşılır.",
        "Scheduled time is in the past; it will publish right away once approved.",
    ),
}


def _f(level: str, code: str, lang: str, **kw: Any) -> dict[str, str]:
    tr, en = M[code]
    msg = (tr if lang == "tr" else en).format(**kw)
    return {"level": level, "code": code, "message": msg}


def all_hashtags(post: dict[str, Any]) -> list[str]:
    seen: list[str] = []
    for t in [
        *(post.get("hashtags") or []),
        *HASHTAG.findall(post.get("caption") or ""),
        *HASHTAG.findall(post.get("first_comment") or ""),
    ]:
        t = t.lower().lstrip("#")
        if t and t not in seen:
            seen.append(t)
    return seen


def check_post(
    post: dict[str, Any],
    media: list[dict[str, Any] | None],
    brand: Brand,
    *,
    lang: str = "tr",
    now: float | None = None,
    tz_hour=None,
    has_account: bool = True,
) -> list[dict[str, str]]:  # noqa: ANN001
    """Returns findings for a post dict (as stored) and its media rows (in order; None for missing ones)."""
    out: list[dict[str, str]] = []
    fmt = post.get("format", "post")
    caption = post.get("caption") or ""
    text_all = "\n".join(
        [caption, post.get("first_comment") or "", post.get("story_text") or "", post.get("alt_text") or ""]
    )

    if not has_account:
        out.append(_f("warn", "no_account", lang))

    # Media
    if not media:
        out.append(_f("error", "no_media", lang))
    if any(m is None for m in media):
        out.append(_f("error", "media_missing", lang))
    items = [m for m in media if m]
    if fmt == "carousel" and not CAROUSEL_ITEMS[0] <= len(media) <= CAROUSEL_ITEMS[1]:
        out.append(_f("error", "carousel_count", lang, n=len(media)))
    if fmt == "reel" and items and items[0]["kind"] != "video":
        out.append(_f("error", "reel_needs_video", lang))
    if fmt == "post" and items and items[0]["kind"] != "image":
        out.append(_f("error", "post_needs_image", lang))
    for m in items:
        title = m.get("title") or m.get("filename") or "?"
        w, h = m.get("width") or 0, m.get("height") or 0
        r = (w / h) if w and h else None
        if r is not None:
            if fmt in {"post", "carousel"} and not (FEED_RATIO[0] - 0.01 <= r <= FEED_RATIO[1] + 0.01):
                out.append(_f("error", "feed_ratio", lang, t=title, r=f"{r:.2f}"))
            if fmt in {"reel", "story"} and not (VERTICAL_RATIO[0] <= r <= VERTICAL_RATIO[1]):
                out.append(
                    _f(
                        "warn" if m["kind"] == "video" else "info",
                        "vertical_ratio",
                        lang,
                        t=title,
                        f="Reels" if fmt == "reel" else ("hikâye" if lang == "tr" else "Story"),
                    )
                )
        if m["kind"] == "image":
            if (m.get("size") or 0) > IMAGE_MAX_BYTES:
                out.append(_f("warn", "image_big", lang, t=title))
            if m.get("mime") not in {"image/jpeg", "image/jpg"}:
                out.append(_f("info", "image_format", lang, t=title))
        if m["kind"] == "video" and m.get("duration"):
            s = round(float(m["duration"]), 1)
            if fmt == "reel":
                if not REEL_SECONDS[0] <= s <= REEL_SECONDS[1]:
                    out.append(_f("error", "reel_len", lang, s=s))
                elif s > 90:
                    out.append(_f("warn", "reel_long", lang, s=s))
            if fmt == "story" and not STORY_VIDEO_SECONDS[0] <= s <= STORY_VIDEO_SECONDS[1]:
                out.append(_f("error", "story_len", lang, s=s))

    # Text
    if fmt != "story":
        if not caption.strip():
            out.append(_f("warn", "empty_caption", lang))
        if len(caption) > CAPTION_MAX:
            out.append(_f("error", "caption_long", lang, n=len(caption)))
        tags = all_hashtags(post)
        if len(tags) > MAX_HASHTAGS:
            out.append(_f("error", "too_many_tags", lang, n=len(tags)))
        first_line = caption.strip().split("\n", 1)[0] if caption.strip() else ""
        if len(first_line) > 125:
            out.append(_f("info", "hook_long", lang, n=len(first_line)))
        if URL.search(caption):
            out.append(_f("info", "url", lang))
        if fmt in {"post", "carousel"} and not (post.get("alt_text") or "").strip():
            out.append(_f("info", "no_alt", lang))
    else:
        out.append(_f("info", "story_no_link", lang))

    for p in dict.fromkeys(placeholders(text_all)):
        out.append(_f("error", "placeholder", lang, p=p))
    low = text_all.lower()
    for w in brand.banned_words:
        if w.strip() and w.strip().lower() in low:
            out.append(_f("error", "banned", lang, w=w.strip()))

    if post.get("sponsored"):
        disclosure_src = caption if fmt != "story" else (post.get("story_text") or "")
        m_ad = AD_TAGS.search(disclosure_src) or any(
            t in {"reklam", "işbirliği", "tanıtım", "ad", "sponsored", "reklama", "oglas", "reclama"}
            for t in (post.get("hashtags") or [])
        )
        if not m_ad:
            out.append(_f("error", "sponsored_tag", lang))
        elif fmt != "story":
            pos = AD_TAGS.search(caption)
            if pos and pos.start() > 125:
                out.append(_f("warn", "sponsored_early", lang))
    if post.get("ai_label"):
        out.append(_f("info", "ai_label", lang))
        if fmt != "story" and not re.search(
            r"yapay zek|\bAI\b|artificial intelligence|veštačk|umjetn|inteligență artificială", caption, re.I
        ):
            out.append(_f("warn", "ai_label_text", lang))

    if DISCOUNT.search(text_all):
        out.append(_f("warn", "discount", lang))
    for rx, code in ((SUPERLATIVE, "superlative"), (HEALTH, "health"), (GUARANTEE, "guarantee")):
        m = rx.search(text_all)
        if m:
            out.append(_f("warn", code, lang, w=m.group(0)))

    # Timing
    sched = post.get("scheduled_at")
    if sched and now is not None and sched < now - 60:
        out.append(_f("info", "past", lang))
    if sched and tz_hour is not None:
        h = tz_hour(sched)
        a, b = brand.rhythm.quiet_start, brand.rhythm.quiet_end
        inside = (a <= h or h < b) if a > b else (a <= h < b)
        if a != b and inside:
            out.append(_f("warn", "quiet_hours", lang, a=a, b=b))

    order = {"error": 0, "warn": 1, "info": 2}
    out.sort(key=lambda f: order[f["level"]])
    return out


def blocking(findings: list[dict[str, str]]) -> bool:
    return any(f["level"] == "error" for f in findings)
