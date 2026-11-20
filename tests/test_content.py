from datetime import date

from tellal.brand import Brand, Product, bio_suggestions
from tellal.content import (
    FORMATS,
    MAX_HASHTAGS,
    PILLARS,
    generate,
    hashtag_slug,
    placeholders,
    special_days,
    upcoming_occasions,
)

BRAND = Brand(
    name="Lale Deri",
    sector="deri",
    city="Sakarya",
    usps=["El dikişi"],
    brand_hashtag="lalederi",
    cta="whatsapp",
    whatsapp="0555 000 00 00",
    products=[Product(name="Siyah Çanta", price="3.950 TL")],
    languages=["tr", "en"],
)
MEDIA = [{"id": 1, "title": "Siyah Çanta", "notes": "Kilitli kapak. İç cep var.", "kind": "image"}]


def test_every_format_and_pillar_produces_a_valid_draft():
    for fmt in FORMATS:
        for pillar in PILLARS:
            d = generate(BRAND, MEDIA, fmt, pillar, seed=1)
            assert len(d.hashtags) <= MAX_HASHTAGS
            if fmt == "story":
                assert d.caption == "" and len(d.story_frames) == 3
            else:
                assert d.caption and len(d.caption) <= 2200
                assert len(d.caption.split("\n")[0]) <= 125


def test_same_seed_same_text_new_seed_new_text():
    a = generate(BRAND, MEDIA, "post", "urun", seed=1)
    b = generate(BRAND, MEDIA, "post", "urun", seed=1)
    texts = {generate(BRAND, MEDIA, "post", "urun", seed=s).caption for s in range(8)}
    assert a.caption == b.caption and len(texts) > 1


def test_nothing_is_invented():
    # Offers and reviews need real facts from the owner: they come out as placeholders.
    assert placeholders(generate(BRAND, MEDIA, "post", "kampanya").caption)
    assert placeholders(generate(BRAND, MEDIA, "post", "kanit").caption)
    # A known product's price is used; nothing else is.
    assert "3.950 TL" in generate(BRAND, MEDIA, "post", "urun").caption


def test_sponsored_disclosure_is_in_the_first_line_and_counts_toward_the_tag_limit():
    d = generate(BRAND, MEDIA, "post", "urun", sponsored=True)
    assert "#reklam" in d.caption.split("\n")[0]
    assert len(d.hashtags) <= MAX_HASHTAGS - 1


def test_other_languages():
    for lang in ["en", "sr", "hr", "ro"]:
        d = generate(BRAND, MEDIA, "reel", "urun", lang=lang)
        assert d.lang == lang and d.reel_script


def test_hashtag_slug_handles_turkish():
    assert hashtag_slug("İstanbul Çanta") == "istanbulçanta"
    assert hashtag_slug("#Işık!") == "ışık"


def test_occasions():
    days = dict(special_days(2026))
    assert days["Anneler Günü"] == date(2026, 5, 10)
    assert days["Efsane Cuma / Black Friday"] == date(2026, 11, 27)
    names = [o["name"] for o in upcoming_occasions(date(2026, 11, 20), 10)]
    assert "Öğretmenler Günü" in names


def test_bios_fit_instagram_limit():
    for b in bio_suggestions(BRAND):
        assert 0 < len(b) <= 150
