"""Comments: sort them by intent and draft a reply. Nothing is sent without the owner's approval.

Complaints are never answered with a template; they are flagged so the owner deals with them in person.
Spam is suggested for hiding, not answered.
"""

from __future__ import annotations

import re
from typing import Any

from .brand import Brand

INTENTS = {
    "sikayet": r"gelmedi|bozuk|iade|şikayet|sikayet|rezalet|memnun değil|kötü|yanlış ürün|cevap vermiyorsunuz|dolandır",
    "spam": r"takipçi|takipci|profilime bak|kazan(mak)? ister|dm at kazan|bit\.ly|link in bio|promo|crypto|kripto",
    "fiyat": r"fiyat|kaç ?tl|kaç para|ne kadar|ücret|price|how much|cena|cijena|preț|pret",
    "stok": r"stok|beden|numara|renk|rengi|var mı|kaldı mı|size|colou?r|in stock",
    "siparis": r"sipariş|siparis|kargo|teslim|ödeme|kapıda|nasıl al|order|shipping|delivery",
    "soru": r"\?|açık mı|saat kaç|adres|nerede|where|when",
    "ovgu": r"güzel|harika|bayıldım|süper|muhteşem|emeğinize|sağlık|tebrik|❤|😍|👏|🔥|love|beautiful|amazing",
}
ORDER = ["sikayet", "spam", "fiyat", "siparis", "stok", "soru", "ovgu"]
LABELS = {
    "sikayet": "Şikâyet",
    "spam": "Spam",
    "fiyat": "Fiyat sorusu",
    "stok": "Stok / beden",
    "siparis": "Sipariş",
    "soru": "Soru",
    "ovgu": "Övgü",
    "diger": "Diğer",
}


def classify(text: str) -> str:
    t = (text or "").lower()
    for k in ORDER:
        if re.search(INTENTS[k], t):
            return k
    return "diger"


def _contact(b: Brand) -> str:
    return {
        "dm": "DM'den yazarsanız hemen yardımcı olalım",
        "whatsapp": f"WhatsApp'tan ({b.whatsapp}) yazarsanız hemen yardımcı olalım"
        if b.whatsapp
        else "WhatsApp'tan yazarsanız hemen yardımcı olalım",
        "link": "tüm detaylar biyografideki linkte",
        "visit": "mağazamızda da görebilirsiniz",
        "call": f"{b.phone} numarasından bize ulaşabilirsiniz" if b.phone else "telefonla bize ulaşabilirsiniz",
    }[b.cta]


def draft_reply(comment: dict[str, Any], brand: Brand, post: dict[str, Any] | None = None) -> str:
    intent = comment.get("intent") or classify(comment.get("text", ""))
    user = comment.get("username") or ""
    at = f"@{user} " if user else ""
    c = _contact(brand)
    price = ""
    if post and intent == "fiyat":
        cap = (post.get("caption") or "").lower()
        for p in brand.products:
            if p.price and p.name.lower() in cap:
                price = p.price
                break
    return {
        "fiyat": f"{at}Merhaba! Fiyatı {price}. {c[0].upper() + c[1:]} 🙏"
        if price
        else f"{at}Merhaba! Fiyat ve detaylar için {c} 🙏",
        "stok": f"{at}Merhaba! Güncel renk ve beden durumu için {c} 🙏",
        "siparis": f"{at}Merhaba! Sipariş için {c}. Kargo ve ödeme seçeneklerini de oradan paylaşıyoruz 🙏",
        "soru": f"{at}Merhaba! {c[0].upper() + c[1:]} 🙏",
        "ovgu": f"{at}Çok teşekkür ederiz, ne güzel bir yorum 🤍",
        "diger": f"{at}Teşekkürler! Sorunuz olursa {c} 🙏",
        "sikayet": "",
        "spam": "",
    }[intent]
