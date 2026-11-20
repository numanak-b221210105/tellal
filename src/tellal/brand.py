"""Brand profile: who the business is, how it talks, what it sells, how often it posts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Lang = Literal["tr", "en", "sr", "ro", "hr"]
Tone = Literal["samimi", "profesyonel", "eglenceli", "zarif", "sade"]

SECTORS: dict[str, dict[str, list[str] | str]] = {
    "kafe": {"label": "Kafe / restoran", "tags": ["kahve", "kafe", "tatlı", "kahvaltı"], "noun": "lezzet"},
    "giyim": {"label": "Giyim / moda", "tags": ["moda", "kombin", "stil", "yenisezon"], "noun": "parça"},
    "deri": {"label": "Deri / kürk / çanta", "tags": ["deri", "deriçanta", "elyapımı", "hakikideri"], "noun": "parça"},
    "guzellik": {"label": "Güzellik / kuaför", "tags": ["güzellik", "bakım", "saç", "makyaj"], "noun": "bakım"},
    "elyapimi": {"label": "El yapımı / atölye", "tags": ["elyapımı", "elişi", "tasarım", "atölye"], "noun": "ürün"},
    "ev": {"label": "Ev / dekorasyon", "tags": ["dekorasyon", "evdekorasyonu", "evim", "tasarım"], "noun": "ürün"},
    "gida": {"label": "Gıda üreticisi", "tags": ["doğal", "yöresel", "lezzet", "evyapımı"], "noun": "lezzet"},
    "spor": {"label": "Spor / sağlıklı yaşam", "tags": ["spor", "antrenman", "fitness", "hareket"], "noun": "program"},
    "hizmet": {"label": "Hizmet / danışmanlık", "tags": ["hizmet", "danışmanlık", "çözüm", "destek"], "noun": "hizmet"},
    "diger": {"label": "Diğer", "tags": ["yeni", "keşfet"], "noun": "ürün"},
}


class Product(BaseModel):
    name: str
    price: str = ""
    notes: str = ""


class Rhythm(BaseModel):
    posts_per_week: int = Field(3, ge=0, le=14)
    reels_per_week: int = Field(3, ge=0, le=14)
    stories_per_day: int = Field(1, ge=0, le=6)
    # Hours (local time) the business never wants anything published.
    quiet_start: int = Field(23, ge=0, le=23)
    quiet_end: int = Field(8, ge=0, le=23)


class Brand(BaseModel):
    name: str = "Markam"
    handle: str = ""
    sector: str = "diger"
    city: str = ""
    description: str = ""
    audience: str = ""
    tone: Tone = "samimi"
    emoji: int = Field(1, ge=0, le=2)
    languages: list[Lang] = Field(default_factory=lambda: ["tr"])
    usps: list[str] = Field(default_factory=list)
    products: list[Product] = Field(default_factory=list)
    banned_words: list[str] = Field(default_factory=list)
    brand_hashtag: str = ""
    cta: Literal["dm", "whatsapp", "link", "visit", "call"] = "dm"
    whatsapp: str = ""
    phone: str = ""
    address: str = ""
    link: str = ""
    rhythm: Rhythm = Field(default_factory=Rhythm)
    ai_label_default: bool = False
    goals: list[Literal["satis", "bilinirlik", "topluluk"]] = Field(default_factory=lambda: ["satis"])

    @property
    def primary_lang(self) -> str:
        return self.languages[0] if self.languages else "tr"


def load_brand(store) -> Brand:  # noqa: ANN001 - Store from db
    data = store.get("brand")
    return Brand.model_validate(data) if data else Brand()


def save_brand(store, brand: Brand) -> None:  # noqa: ANN001
    store.put("brand", brand.model_dump())


def bio_suggestions(b: Brand) -> list[str]:
    """Instagram bios are at most 150 characters. The API cannot change them, so these are for copying."""
    sector = str(SECTORS.get(b.sector, SECTORS["diger"])["label"]).split(" / ")[0]
    usp = b.usps[0] if b.usps else (b.description.split(".")[0] if b.description else sector)
    where = f"📍 {b.city}" if b.city else ""
    cta = {
        "dm": "💬 Sipariş için DM",
        "whatsapp": "📲 WhatsApp ile sipariş" + (f": {b.whatsapp}" if b.whatsapp else ""),
        "link": "🔗 Tüm ürünler aşağıda",
        "visit": "🕘 Mağazamıza bekleriz",
        "call": "📞 Bilgi için arayın" + (f": {b.phone}" if b.phone else ""),
    }[b.cta]
    tag = f"#{b.brand_hashtag}" if b.brand_hashtag else ""
    raw = [
        "\n".join(x for x in [usp, where, cta] if x),
        "\n".join(x for x in [f"{sector} · {b.city}" if b.city else sector, f"✨ {usp}", cta, tag] if x),
        "\n".join(x for x in [f"{b.name}: {usp}", "Her hafta yeni ürünler", cta] if x),
        "\n".join(
            x
            for x in [
                usp,
                "Kendi üretimimiz, özenle hazırlanır"
                if b.sector in {"elyapimi", "gida", "deri"}
                else "Size özel çözümler",
                where,
            ]
            if x
        ),
    ]
    out: list[str] = []
    for r in raw:
        r = r.strip()
        if len(r) > 150:
            r = r[:147].rstrip() + "…"
        if r and r not in out:
            out.append(r)
    return out
