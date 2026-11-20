from tellal.brand import Brand
from tellal.compliance import blocking, check_post

BRAND = Brand(banned_words=["ucuz"])
IMG = {"id": 1, "kind": "image", "mime": "image/jpeg", "width": 1080, "height": 1350, "size": 200_000, "title": "a"}


def codes(post, media=None, **kw):
    return {f["code"] for f in check_post(post, media if media is not None else [IMG], BRAND, **kw)}


def test_clean_post_has_no_errors():
    f = check_post({"format": "post", "caption": "Yeni ürün.", "hashtags": ["a"], "alt_text": "x"}, [IMG], BRAND)
    assert not blocking(f)


def test_limits():
    assert "caption_long" in codes({"format": "post", "caption": "x" * 2300})
    assert "too_many_tags" in codes({"format": "post", "caption": "#a #b", "hashtags": ["c", "d", "e", "f"]})
    assert "carousel_count" in codes({"format": "carousel", "caption": "x"})
    wide = {**IMG, "width": 2000, "height": 800}
    assert "feed_ratio" in codes({"format": "post", "caption": "x"}, [wide])
    video = {"id": 2, "kind": "video", "mime": "video/mp4", "width": 720, "height": 1280, "duration": 1.0}
    assert "reel_len" in codes({"format": "reel", "caption": "x"}, [video])
    assert "reel_needs_video" in codes({"format": "reel", "caption": "x"})


def test_turkish_ad_rules():
    assert "sponsored_tag" in codes({"format": "post", "caption": "Harika ürün", "sponsored": True})
    assert "sponsored_tag" not in codes({"format": "post", "caption": "#reklam Harika ürün", "sponsored": True})
    assert "discount" in codes({"format": "post", "caption": "Bu hafta %20 indirim"})
    assert "health" in codes({"format": "post", "caption": "Bu çay kilo verdirir"})
    assert "superlative" in codes({"format": "post", "caption": "Türkiye'nin en iyi çantası"})
    assert "ai_label_text" in codes({"format": "post", "caption": "Yeni", "ai_label": True})


def test_placeholders_and_banned_words_block():
    assert blocking(check_post({"format": "post", "caption": "[Kampanya detayı]"}, [IMG], BRAND))
    assert blocking(check_post({"format": "post", "caption": "Çok ucuz"}, [IMG], BRAND))


def test_quiet_hours():
    f = codes({"format": "post", "caption": "x", "scheduled_at": 1}, tz_hour=lambda ts: 2)
    assert "quiet_hours" in f
