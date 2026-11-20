"""Turns a business's own photo or video into ready drafts: feed post, carousel, Reel or Story.

Two engines share one output shape:
- "sablon": a template engine that needs nothing (works offline and in the browser);
- "llm": any OpenAI-compatible model, used when reachable; its output goes through the same
  limits and checks, and anything missing is filled from the template draft.

Design rules that come from how Instagram ranks content (watch time, sends and likes per reach):
the first ~125 characters carry the hook, the call to action invites a *send* or a *save*,
at most 5 hashtags (Instagram's limit since December 2025), Reels are planned short enough to be
watched to the end. Nothing is invented: no fake reviews, prices or offers; missing facts become
[placeholders] that the checker refuses to publish.
"""

from __future__ import annotations

import random
import re
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any

from .brand import SECTORS, Brand

FORMATS = ("post", "carousel", "reel", "story")
PILLARS = ("urun", "surec", "ipucu", "topluluk", "kampanya", "kanit")
MAX_HASHTAGS = 5
PLACEHOLDER = re.compile(r"\[[^\]]{2,80}\]")

# ---------------------------------------------------------------------------
# Phrase banks. {p} product, {b} brand, {usp} selling point, {city}, {noun} sector noun, {occ} occasion.
# Turkish templates keep {p} in the nominative so suffixes never break.

BANK: dict[str, dict[str, list[str]]] = {
    "tr": {
        "hook_urun": [
            "{p} geldi ve beklediğimizden de güzel oldu.",
            "Bu hafta en çok sorulan: {p}.",
            "Yakından bakın: {p}.",
            "{p}: {usp}.",
            "Yeni sezonun favorisi hazır: {p}.",
            "Raflardan hızlı gidiyor: {p}.",
        ],
        "hook_surec": [
            "Bir {p} nasıl hazırlanıyor? Kamera arkasına buyrun.",
            "Kimsenin görmediği kısım: {p} hazırlanırken.",
            "Atölyemizden bir gün: bugün sırada {p} var.",
            "Sabırla, elde: {p} böyle ortaya çıkıyor.",
        ],
        "hook_ipucu": [
            "{p} alırken çoğu kişinin atladığı detaylar 👇",
            "{p} hakkında en çok sorulan sorular ve cevapları.",
            "{p} uzun yıllar ilk günkü gibi kalsın diye küçük ipuçları.",
            "Kaydedin, lazım olacak: {p} rehberi.",
        ],
        "hook_topluluk": [
            "Karar sizin: {p} için hangi seçeneği seçerdiniz?",
            "Dürüst olun: {p} sizin tarzınız mı?",
            "{p} için bir isim arıyoruz, öneriniz var mı?",
            "Bir soru: {p} en çok hangi anınıza eşlik ederdi?",
        ],
        "hook_kampanya": [
            "Bu haftaya özel: {p}.",
            "Kısa süreliğine: {p} için fırsat başladı.",
            "{occ} için hazırladık: {p}.",
        ],
        "hook_kanit": [
            "Sizden gelen bu mesaj günümüzü güzelleştirdi.",
            "{p} için gelen yorumlardan biri:",
        ],
        "body_default": [
            "{usp}. Her detayını özenle seçtik.",
            "{b} olarak işimizi severek yapıyoruz; {p} de bunun küçük bir örneği.",
            "Kendi gözünüzle görmeniz için yakın çekim paylaştık.",
        ],
        "body_surec": [
            "Her aşaması özen istiyor; acele etmiyoruz.",
            "Bitmiş ürünü herkes görür, biz de emeği göstermek istedik.",
        ],
        "body_topluluk": ["Yorumlarda buluşalım, en çok önerilen seçeneği bir sonraki paylaşımda göstereceğiz."],
        "body_kanit": ["[Müşteri yorumu: gerçek bir yorumu, sahibinin izniyle buraya ekleyin]"],
        "body_kampanya": ["[Kampanya detayı: indirim oranı, eski ve yeni fiyat, bitiş tarihi]"],
        "send": [
            "Bunu sevecek birini tanıyorsanız ona gönderin 💌",
            "Aklınıza gelen o kişiye gönderin, sonra bize teşekkür eder 😊",
            "Lazım olacak birine iletmeyi unutmayın.",
        ],
        "save": ["Kaydedin, sonra lazım olur 📌", "Sonra dönüp bakmak için kaydedin."],
        "cta_dm": ["Sipariş ve bilgi için DM'den yazın.", "Detaylar için mesaj atmanız yeterli."],
        "cta_whatsapp": ["WhatsApp'tan sipariş: {whatsapp}", "Hızlı sipariş için WhatsApp: {whatsapp}"],
        "cta_link": ["Tüm detaylar biyografideki linkte.", "Sipariş linki profilimizde."],
        "cta_visit": ["Mağazamızda görmek için sizi de bekleriz{address}.", "Uğrayın, birlikte bakalım{address}."],
        "cta_call": ["Bilgi için arayın: {phone}", "Sorularınız için: {phone}"],
        "price": ["Fiyat: {price}"],
        "alt": ["{p} ürününün yakın çekim fotoğrafı.", "{b} tarafından paylaşılan {p} görseli."],
        "story_detail": ["{usp}", "Detaylar için tıklayın"],
        "story_cta": ["DM'den yazın 💬", "Ankete katılın 👇", "Sorularınızı bekliyoruz"],
        "sticker": ['Anket ekle: "Hangisi?"', 'Soru kutusu ekle: "Ne merak ediyorsunuz?"', "Link çıkartması ekle"],
        "reel_shot_open": ["Ürün yakın planda, hafif hareketle (ilk 2 saniye)", "El girer, ürünü kaldırır"],
        "reel_shot_mid": ["Detaylar: doku, renk, kullanım", "Ürün kullanımda, gerçek bir anda"],
        "reel_shot_end": ["Ürün ve logo, sade bir kapanış", "Gülümseyen bir yüz ya da paket hazırlanırken"],
        "carousel_next": ["Kaydırın 👉", "Detaylar sonraki karede"],
        "label_ai": "Bu içerikte yapay zekâ ile oluşturulmuş görsel öğeler bulunmaktadır.",
        "label_ad": "#reklam",
    },
    "en": {
        "hook_urun": [
            "{p} is here, and it turned out even better than we hoped.",
            "The one you keep asking about: {p}.",
            "Take a closer look: {p}.",
            "{p}: {usp}.",
            "This season's favourite is ready: {p}.",
        ],
        "hook_surec": [
            "How is {p} made? Come behind the scenes.",
            "The part nobody sees: making {p}.",
            "A day at {b}: today it's {p}.",
        ],
        "hook_ipucu": [
            "What most people miss when buying {p} 👇",
            "Your questions about {p}, answered.",
            "Save this: a quick guide to {p}.",
        ],
        "hook_topluluk": [
            "You decide: which {p} would you pick?",
            "Be honest: is {p} your style?",
            "We need a name for {p}. Ideas?",
        ],
        "hook_kampanya": ["This week only: {p}.", "For a short time: an offer on {p}.", "Ready for {occ}: {p}."],
        "hook_kanit": ["This message made our day.", "One of the reviews we got for {p}:"],
        "body_default": [
            "{usp}. Every detail is chosen with care.",
            "At {b} we love what we do, and {p} shows it.",
            "We filmed it up close so you can see for yourself.",
        ],
        "body_surec": [
            "Every step takes care, and we never rush it.",
            "Everyone sees the finished piece; we wanted to show the work.",
        ],
        "body_topluluk": ["Tell us in the comments; we'll show the most popular pick next time."],
        "body_kanit": ["[Customer review: add a real review here, with the customer's permission]"],
        "body_kampanya": ["[Offer details: discount, old and new price, end date]"],
        "send": ["Know someone who'd love this? Send it to them 💌", "Send this to the friend who needs it."],
        "save": ["Save this for later 📌", "Save it so you can find it again."],
        "cta_dm": ["Send us a DM to order.", "Questions? Just send a message."],
        "cta_whatsapp": ["Order on WhatsApp: {whatsapp}"],
        "cta_link": ["Details at the link in our bio.", "Order link in our profile."],
        "cta_visit": ["Come and see it in store{address}.", "Drop by, we'd love to show you{address}."],
        "cta_call": ["Call us: {phone}"],
        "price": ["Price: {price}"],
        "alt": ["Close-up photo of {p}.", "{p}, photographed by {b}."],
        "story_detail": ["{usp}", "Tap for details"],
        "story_cta": ["DM us 💬", "Vote below 👇", "Ask us anything"],
        "sticker": ['Add a poll: "Which one?"', "Add a question box", "Add a link sticker"],
        "reel_shot_open": ["Product in close-up with gentle motion (first 2 seconds)", "A hand picks up the product"],
        "reel_shot_mid": ["Details: texture, colour, use", "The product in a real moment"],
        "reel_shot_end": ["Product and logo, a clean ending", "A smile, or an order being packed"],
        "carousel_next": ["Swipe 👉", "More on the next slide"],
        "label_ai": "This content contains AI-generated visual elements.",
        "label_ad": "#ad",
    },
    "sr": {
        "hook_urun": ["Stiglo je: {p}.", "Pogledajte izbliza: {p}.", "{p}: {usp}.", "Novo u ponudi: {p}."],
        "hook_surec": ["Kako nastaje {p}? Pogledajte iza kulisa.", "Deo koji niko ne vidi: pravimo {p}."],
        "hook_ipucu": ["Sačuvajte: kratak vodič za {p}.", "Odgovori na vaša pitanja o {p}."],
        "hook_topluluk": ["Vi birate: koji {p} biste uzeli?", "Iskreno: da li je {p} vaš stil?"],
        "hook_kampanya": ["Samo ove nedelje: {p}.", "Kratko traje: ponuda za {p}."],
        "hook_kanit": ["Ova poruka nam je ulepšala dan."],
        "body_default": ["{usp}. Svaki detalj biramo pažljivo.", "Snimili smo izbliza da vidite sami."],
        "body_surec": ["Svaki korak traži pažnju, ne žurimo."],
        "body_topluluk": ["Napišite u komentarima, najpopularniji izbor pokazujemo sledeći put."],
        "body_kanit": ["[Utisak kupca: dodajte pravi komentar, uz dozvolu]"],
        "body_kampanya": ["[Detalji ponude: popust, stara i nova cena, datum završetka]"],
        "send": ["Pošaljite ovo nekome kome bi se dopalo 💌"],
        "save": ["Sačuvajte za kasnije 📌"],
        "cta_dm": ["Za porudžbinu pošaljite poruku (DM).", "Pitanja? Pišite nam u poruci."],
        "cta_whatsapp": ["Porudžbine preko WhatsApp-a: {whatsapp}"],
        "cta_link": ["Sve detalje naći ćete na linku u opisu profila."],
        "cta_visit": ["Posetite nas u radnji{address}."],
        "cta_call": ["Pozovite nas: {phone}"],
        "price": ["Cena: {price}"],
        "alt": ["Fotografija proizvoda {p} izbliza."],
        "story_detail": ["{usp}"],
        "story_cta": ["Pišite nam 💬", "Glasajte 👇"],
        "sticker": ["Dodajte anketu", "Dodajte polje za pitanja"],
        "reel_shot_open": ["Proizvod izbliza, uz lagan pokret"],
        "reel_shot_mid": ["Detalji: tekstura, boja, upotreba"],
        "reel_shot_end": ["Proizvod i logo, jednostavan kraj"],
        "carousel_next": ["Prevucite 👉"],
        "label_ai": "Ovaj sadržaj sadrži vizuelne elemente napravljene veštačkom inteligencijom.",
        "label_ad": "#reklama",
    },
    "hr": {
        "hook_urun": ["Stiglo je: {p}.", "Pogledajte izbliza: {p}.", "{p}: {usp}.", "Novo u ponudi: {p}."],
        "hook_surec": ["Kako nastaje {p}? Pogledajte iza kulisa."],
        "hook_ipucu": ["Spremite: kratki vodič za {p}.", "Odgovori na vaša pitanja o {p}."],
        "hook_topluluk": ["Vi birate: koji {p} biste odabrali?", "Iskreno: je li {p} vaš stil?"],
        "hook_kampanya": ["Samo ovaj tjedan: {p}.", "Kratko traje: ponuda za {p}."],
        "hook_kanit": ["Ova poruka uljepšala nam je dan."],
        "body_default": ["{usp}. Svaki detalj biramo pažljivo.", "Snimili smo izbliza da vidite sami."],
        "body_surec": ["Svaki korak traži pažnju, ne žurimo."],
        "body_topluluk": ["Napišite u komentarima, najpopularniji odabir pokazujemo sljedeći put."],
        "body_kanit": ["[Dojam kupca: dodajte stvarni komentar, uz dopuštenje]"],
        "body_kampanya": ["[Detalji ponude: popust, stara i nova cijena, datum završetka]"],
        "send": ["Pošaljite ovo nekome kome bi se svidjelo 💌"],
        "save": ["Spremite za kasnije 📌"],
        "cta_dm": ["Za narudžbu pošaljite poruku (DM).", "Pitanja? Pišite nam u poruci."],
        "cta_whatsapp": ["Narudžbe putem WhatsAppa: {whatsapp}"],
        "cta_link": ["Sve detalje pronađite na poveznici u opisu profila."],
        "cta_visit": ["Posjetite nas u trgovini{address}."],
        "cta_call": ["Nazovite nas: {phone}"],
        "price": ["Cijena: {price}"],
        "alt": ["Fotografija proizvoda {p} izbliza."],
        "story_detail": ["{usp}"],
        "story_cta": ["Pišite nam 💬", "Glasajte 👇"],
        "sticker": ["Dodajte anketu", "Dodajte okvir za pitanja"],
        "reel_shot_open": ["Proizvod izbliza, uz lagani pokret"],
        "reel_shot_mid": ["Detalji: tekstura, boja, upotreba"],
        "reel_shot_end": ["Proizvod i logo, jednostavan kraj"],
        "carousel_next": ["Povucite 👉"],
        "label_ai": "Ovaj sadržaj sadrži vizualne elemente izrađene umjetnom inteligencijom.",
        "label_ad": "#oglas",
    },
    "ro": {
        "hook_urun": ["A sosit: {p}.", "Priviți de aproape: {p}.", "{p}: {usp}.", "Nou la noi: {p}."],
        "hook_surec": ["Cum se face {p}? Veniți în culise.", "Partea pe care nu o vede nimeni: pregătim {p}."],
        "hook_ipucu": ["Salvați: un ghid scurt despre {p}.", "Răspunsuri la întrebările voastre despre {p}."],
        "hook_topluluk": ["Voi alegeți: ce variantă de {p} ați lua?", "Sincer: {p} este stilul vostru?"],
        "hook_kampanya": ["Doar săptămâna aceasta: {p}.", "Pentru scurt timp: ofertă la {p}."],
        "hook_kanit": ["Mesajul acesta ne-a făcut ziua mai frumoasă."],
        "body_default": ["{usp}. Alegem fiecare detaliu cu grijă.", "Am filmat de aproape ca să vedeți singuri."],
        "body_surec": ["Fiecare etapă cere atenție, nu ne grăbim."],
        "body_topluluk": ["Scrieți-ne în comentarii; arătăm data viitoare varianta preferată."],
        "body_kanit": ["[Părerea clientului: adăugați o recenzie reală, cu permisiunea lui]"],
        "body_kampanya": ["[Detaliile ofertei: reducere, preț vechi și nou, data de încheiere]"],
        "send": ["Trimiteți asta cuiva căruia i-ar plăcea 💌"],
        "save": ["Salvați pentru mai târziu 📌"],
        "cta_dm": ["Pentru comenzi, trimiteți-ne un mesaj (DM).", "Întrebări? Scrieți-ne un mesaj."],
        "cta_whatsapp": ["Comenzi pe WhatsApp: {whatsapp}"],
        "cta_link": ["Toate detaliile sunt la linkul din bio."],
        "cta_visit": ["Vă așteptăm în magazin{address}."],
        "cta_call": ["Sunați-ne: {phone}"],
        "price": ["Preț: {price}"],
        "alt": ["Fotografie de aproape cu {p}."],
        "story_detail": ["{usp}"],
        "story_cta": ["Scrieți-ne 💬", "Votați 👇"],
        "sticker": ["Adăugați un sondaj", "Adăugați o casetă de întrebări"],
        "reel_shot_open": ["Produsul de aproape, cu o mișcare ușoară"],
        "reel_shot_mid": ["Detalii: textură, culoare, utilizare"],
        "reel_shot_end": ["Produsul și logo-ul, un final simplu"],
        "carousel_next": ["Glisați 👉"],
        "label_ai": "Acest conținut include elemente vizuale generate cu inteligență artificială.",
        "label_ad": "#reclama",
    },
}

EMOJI = {
    "urun": ["✨", "🤍", "🌿", "⭐"],
    "surec": ["🛠️", "🎬", "⏳"],
    "ipucu": ["📌", "💡"],
    "topluluk": ["💭", "🙋"],
    "kampanya": ["🎁", "🔥", "⏰"],
    "kanit": ["💬", "🙏"],
}

# ---------------------------------------------------------------------------
# Special days (Turkey). Lunar holidays are listed for the years we know; check them yearly.

LUNAR = {
    2026: [("Ramazan Bayramı", date(2026, 3, 20)), ("Kurban Bayramı", date(2026, 5, 27))],
    2027: [("Ramazan Bayramı", date(2027, 3, 9)), ("Kurban Bayramı", date(2027, 5, 16))],
}


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def special_days(year: int) -> list[tuple[str, date]]:
    days = [
        ("Yılbaşı", date(year, 1, 1)),
        ("Sevgililer Günü", date(year, 2, 14)),
        ("Dünya Kadınlar Günü", date(year, 3, 8)),
        ("Anneler Günü", _nth_weekday(year, 5, 6, 2)),
        ("Babalar Günü", _nth_weekday(year, 6, 6, 3)),
        ("Okula dönüş", _nth_weekday(year, 9, 0, 2)),
        ("Cumhuriyet Bayramı", date(year, 10, 29)),
        ("Öğretmenler Günü", date(year, 11, 24)),
        ("Efsane Cuma / Black Friday", _nth_weekday(year, 11, 3, 4) + timedelta(days=1)),
        ("Yılbaşı alışverişi", date(year, 12, 20)),
    ]
    return sorted(days + LUNAR.get(year, []), key=lambda x: x[1])


def upcoming_occasions(today: date, horizon_days: int = 21) -> list[dict[str, Any]]:
    out = []
    for y in (today.year, today.year + 1):
        for name, d in special_days(y):
            delta = (d - today).days
            if 0 <= delta <= horizon_days:
                out.append({"name": name, "date": d.isoformat(), "in_days": delta})
    return out


# ---------------------------------------------------------------------------

_TR_LOWER = str.maketrans({"I": "ı", "İ": "i"})


def hashtag_slug(text: str) -> str:
    s = text.translate(_TR_LOWER).lower()
    s = re.sub(r"[^\w]", "", s, flags=re.UNICODE).replace("_", "")
    return s[:30]


def build_hashtags(brand: Brand, title: str, pillar: str, extra: list[str] | None = None) -> list[str]:
    sector = SECTORS.get(brand.sector, SECTORS["diger"])
    st = [str(x) for x in sector["tags"]] + ["", "", ""]
    tags: list[str] = []
    for t in [
        brand.brand_hashtag,
        hashtag_slug(title) if 3 <= len(hashtag_slug(title)) <= 24 else "",
        *(extra or []),
        st[0],
        (hashtag_slug(brand.city) + st[0]) if brand.city else st[1],
        st[2],
        "kamerarkası" if pillar == "surec" else "",
    ]:
        t = hashtag_slug(t) if t else ""
        if t and t not in tags:
            tags.append(t)
    return tags[:MAX_HASHTAGS]


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", (text or "").strip())
    return [p.strip(" -•") for p in parts if len(p.strip(" -•")) > 2]


def _product_info(brand: Brand, title: str) -> dict[str, str]:
    t = title.lower()
    for p in brand.products:
        if p.name and (p.name.lower() in t or t in p.name.lower()):
            return {"price": p.price, "notes": p.notes}
    return {"price": "", "notes": ""}


@dataclass
class Draft:
    format: str
    lang: str
    pillar: str
    caption: str
    hashtags: list[str]
    alt_text: str = ""
    first_comment: str = ""
    story_frames: list[str] = field(default_factory=list)
    sticker: str = ""
    reel_hook: str = ""
    reel_script: list[dict[str, str]] = field(default_factory=list)
    carousel_slides: list[str] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)
    engine: str = "sablon"
    seed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def generate(
    brand: Brand,
    media: list[dict[str, Any]],
    fmt: str = "post",
    pillar: str = "urun",
    lang: str | None = None,
    occasion: str | None = None,
    seed: int = 0,
    sponsored: bool = False,
    ai_label: bool = False,
) -> Draft:
    """Template engine. Deterministic for a given seed, so "rewrite" just changes the seed."""
    if fmt not in FORMATS:
        raise ValueError(f"unknown format: {fmt}")
    if pillar not in PILLARS:
        pillar = "urun"
    lang = lang if lang in BANK else brand.primary_lang if brand.primary_lang in BANK else "tr"
    bank = BANK[lang]
    first = media[0] if media else {}
    title = (first.get("title") or "").strip() or ("ürünümüz" if lang == "tr" else "our product")
    info = _product_info(brand, title)
    notes = " ".join(x for x in [first.get("notes") or "", info["notes"]] if x)
    facts = _sentences(notes)
    usp = (
        brand.usps[0]
        if brand.usps
        else (facts[0].rstrip(".") if facts else ("özenle hazırlandı" if lang == "tr" else "made with care"))
    )
    rng = random.Random(f"{seed}|{fmt}|{pillar}|{lang}|{first.get('id', 0)}|{title}")

    def pick(key: str) -> str:
        opts = bank.get(key) or BANK["en"][key]
        if not occasion:
            opts = [o for o in opts if "{occ}" not in o] or opts
        return rng.choice(opts)

    noun = str(SECTORS.get(brand.sector, SECTORS["diger"])["noun"])
    ctx = {
        "p": title,
        "b": brand.name,
        "usp": usp.rstrip("."),
        "city": brand.city,
        "noun": noun,
        "occ": occasion or ("bu hafta" if lang == "tr" else "this week"),
        "whatsapp": brand.whatsapp or "[WhatsApp numarası]",
        "phone": brand.phone or "[telefon]",
        "address": f" ({brand.address})" if brand.address else "",
        "price": info["price"],
    }
    fill = lambda s: s.format(**ctx)  # noqa: E731
    emo = (lambda: rng.choice(EMOJI[pillar])) if brand.emoji else (lambda: "")
    calm = brand.tone in {"profesyonel", "zarif"}

    hook = fill(pick(f"hook_{pillar}"))
    hook = hook[:1].upper() + hook[1:]
    if brand.emoji == 2 or (brand.emoji and not calm and rng.random() < 0.6):
        hook = f"{hook} {emo()}".strip()

    body: list[str] = []
    if pillar in {"kanit", "kampanya", "topluluk", "surec"}:
        body.append(fill(pick(f"body_{pillar}")))
    if pillar not in {"kanit"}:
        start = 0 if brand.usps else 1
        body.extend(facts[start : start + 2] if pillar != "ipucu" else [f"• {f.rstrip('.')}" for f in facts[:4]])
        if pillar == "ipucu" and not facts:
            body.append("[İpucu 1] · [İpucu 2] · [İpucu 3]" if lang == "tr" else "[Tip 1] · [Tip 2] · [Tip 3]")
        if pillar in {"urun", "surec"} and len(body) < 2:
            body.append(fill(pick("body_default")))
    if info["price"] and pillar in {"urun", "kampanya"}:
        body.append(fill(pick("price")))

    engage = pick("save") if pillar == "ipucu" else pick("send") if pillar in {"urun", "kanit", "surec"} else ""
    cta = fill(pick(f"cta_{brand.cta}"))
    # A paid partnership must be disclosed where it is seen first, not at the end.
    lines = [f"{hook} {bank['label_ad']}" if sponsored else hook, "", *body]
    if engage:
        lines += ["", engage]
    lines += [cta]
    if ai_label:
        lines += ["", bank["label_ai"]]
    tags = build_hashtags(brand, title, pillar)
    if sponsored:
        # The #reklam tag counts toward Instagram's 5-hashtag limit.
        tags = tags[: MAX_HASHTAGS - 1]
    caption = "\n".join(lines).strip()
    caption = re.sub(r"\n{3,}", "\n\n", caption)

    d = Draft(format=fmt, lang=lang, pillar=pillar, caption=caption, hashtags=tags, seed=seed)
    d.rationale.append(
        "İlk satır kanca: açıklamanın yalnızca ilk ~125 karakteri 'devamı'na basmadan görünür."
        if lang == "tr"
        else "The first line is the hook: only ~125 characters show before 'more'."
    )
    if engage:
        d.rationale.append(
            "Kapanış bir 'gönder' ya da 'kaydet' daveti: Instagram'ın en güçlü sıralama sinyalleri arasında erişim başına gönderilme ve kaydetme var."
            if lang == "tr"
            else "The closing line invites a send or a save: sends per reach is one of the strongest ranking signals."
        )
    d.rationale.append(
        f"{len(tags)} hashtag: Instagram Aralık 2025'ten beri gönderi başına en fazla 5'e izin veriyor."
        if lang == "tr"
        else f"{len(tags)} hashtags: Instagram allows at most 5 per post since December 2025."
    )

    if fmt in {"post", "carousel"}:
        d.alt_text = fill(pick("alt"))
    if fmt == "carousel":
        n = max(2, min(10, len(media)))
        slides = [hook] + [f"{i + 1}/{n} · {f}" for i, f in enumerate(facts[: n - 2])]
        while len(slides) < n - 1:
            slides.append(fill(pick("body_default")))
        slides.append(cta)
        d.carousel_slides = slides[:n]
        d.caption = d.caption.replace(hook, f"{hook}\n{pick('carousel_next')}", 1)
    if fmt == "reel":
        short = hook.split(":")[0] if ":" in hook else hook
        d.reel_hook = short if len(short) <= 60 else short[:60].rsplit(" ", 1)[0] + "…"
        d.reel_script = [
            {"t": "0–2 sn" if lang == "tr" else "0–2 s", "shot": pick("reel_shot_open"), "text": d.reel_hook},
            {"t": "2–7 sn" if lang == "tr" else "2–7 s", "shot": pick("reel_shot_mid"), "text": usp},
            {"t": "7–11 sn" if lang == "tr" else "7–11 s", "shot": pick("reel_shot_end"), "text": cta},
        ]
        d.rationale.append(
            "7–12 saniyelik kurgu: izlenme süresi ve tekrar izlenme Reels'te en önemli sinyal; kısa ve sonuna kadar izlenen video uzun ve yarıda bırakılandan daha iyi sinyal verir."
            if lang == "tr"
            else "7–12 seconds: watch time and replays matter most for Reels; a short video watched to the end beats a long one abandoned halfway."
        )
    if fmt == "story":
        d.story_frames = [hook, fill(pick("story_detail")), fill(pick("story_cta"))]
        d.sticker = pick("sticker")
        d.caption = ""
        d.hashtags = []
        d.rationale.append(
            "Hikâyelerde açıklama yok; metin görselin üzerine yazılır. Etkileşim çıkartmalarını API ekleyemez, paylaşımdan sonra uygulamadan ekleyebilirsiniz."
            if lang == "tr"
            else "Stories have no caption; text goes on the image. The API cannot add interactive stickers; add them in the app after posting."
        )
    return d


def placeholders(text: str) -> list[str]:
    return PLACEHOLDER.findall(text or "")


# ---------------------------------------------------------------------------
# Optional LLM engine


def llm_generate(
    brand: Brand,
    media: list[dict[str, Any]],
    fmt: str,
    pillar: str,
    lang: str,
    occasion: str | None,
    seed: int,
    sponsored: bool,
    ai_label: bool,
    chat,
) -> Draft:  # noqa: ANN001 - chat callable
    """Asks an LLM for the same fields. Falls back to the template draft for anything missing or invalid."""
    base = generate(brand, media, fmt, pillar, lang, occasion, seed, sponsored, ai_label)
    first = media[0] if media else {}
    lang_name = {"tr": "Turkish", "en": "English", "sr": "Serbian (Latin script)", "ro": "Romanian", "hr": "Croatian"}[
        base.lang
    ]
    system = (
        "You write Instagram content for a small business. Reply with JSON only. Rules: write in "
        f"{lang_name}; tone '{brand.tone}'; emoji level {brand.emoji} of 2; the first line is a hook under 125 characters; "
        "end with an invitation to send the post to someone or to save it, then the call to action; "
        f"at most {MAX_HASHTAGS} hashtags in total, as a list without '#'; never invent customer reviews, prices, discounts, "
        "awards or health claims; if a needed fact is missing write it as [placeholder]; never use these words: "
        f"{', '.join(brand.banned_words) or '-'}."
    )
    user = {
        "brand": brand.model_dump(
            include={"name", "sector", "city", "description", "audience", "usps", "cta", "whatsapp", "phone", "link"}
        ),
        "media": {
            "title": first.get("title"),
            "notes": first.get("notes"),
            "kind": first.get("kind"),
            "count": len(media),
        },
        "format": fmt,
        "pillar": pillar,
        "occasion": occasion,
        "sponsored_disclosure_needed": sponsored,
        "ai_generated_visuals": ai_label,
        "return": {
            "caption": "str",
            "hashtags": ["str"],
            "alt_text": "str (post/carousel only)",
            "reel_hook": "str (reel only)",
            "story_frames": ["str (story only, 3 short lines)"],
            "carousel_slides": ["str (carousel only)"],
        },
    }
    out = chat(system, user)
    if not isinstance(out, dict):
        return base
    d = Draft(**{**base.to_dict(), "engine": "llm"})
    if isinstance(out.get("caption"), str) and fmt != "story" and 10 <= len(out["caption"]) <= 2200:
        d.caption = out["caption"].strip()
        if sponsored and BANK[d.lang]["label_ad"] not in d.caption:
            first, _, rest = d.caption.partition("\n")
            d.caption = f"{first} {BANK[d.lang]['label_ad']}" + (f"\n{rest}" if rest else "")
        if ai_label and BANK[d.lang]["label_ai"] not in d.caption:
            d.caption += "\n\n" + BANK[d.lang]["label_ai"]
    if isinstance(out.get("hashtags"), list) and fmt != "story":
        tags = [hashtag_slug(str(t)) for t in out["hashtags"] if hashtag_slug(str(t))]
        if tags:
            d.hashtags = list(dict.fromkeys(tags))[: MAX_HASHTAGS - (1 if sponsored else 0)]
    for k in ("alt_text", "reel_hook"):
        if isinstance(out.get(k), str) and out[k].strip() and getattr(base, k):
            setattr(d, k, out[k].strip()[:300])
    for k in ("story_frames", "carousel_slides"):
        if isinstance(out.get(k), list) and out[k] and getattr(base, k):
            setattr(d, k, [str(x)[:200] for x in out[k]][:10])
    # Hashtags written inside the caption count toward the limit too: keep them out of it.
    ad = BANK[d.lang]["label_ad"]
    d.caption = re.sub(r"(?<!\S)#\w+", lambda m: m.group(0) if m.group(0) == ad else "", d.caption)
    d.caption = re.sub(r"[ \t]+\n", "\n", d.caption).strip()
    d.rationale = [
        "Metin yapay zekâ modeliyle yazıldı, kurallar ve denetim aynı."
        if d.lang == "tr"
        else "Written by the language model; same rules and checks."
    ] + base.rationale[1:]
    return d
