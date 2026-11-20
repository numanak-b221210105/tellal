import json

import httpx
import pytest

from tellal.config import Settings
from tellal.providers import ProviderError, PublishRequest
from tellal.providers.instagram import InstagramProvider

ACC = {"remote_id": "1784", "token": "tok"}


def make(handler):
    calls = []

    def h(req: httpx.Request) -> httpx.Response:
        body = dict(httpx.QueryParams(req.content.decode())) if req.content else {}
        calls.append((req.method, req.url.path, {**dict(req.url.params), **body}))
        return handler(req, calls)

    return InstagramProvider(
        Settings(ig_api_version="v25.0"), transport=httpx.MockTransport(h), sleep=lambda s: None
    ), calls


def test_publish_photo_flow():
    def h(req, calls):
        p = req.url.path
        if p.endswith("/1784/media"):
            return httpx.Response(200, json={"id": "C1"})
        if p.endswith("/C1"):
            return httpx.Response(200, json={"status_code": "FINISHED"})
        if p.endswith("/media_publish"):
            return httpx.Response(200, json={"id": "M1"})
        if p.endswith("/M1"):
            return httpx.Response(200, json={"permalink": "https://instagram.com/p/x"})
        if p.endswith("/M1/comments"):
            return httpx.Response(200, json={"id": "K1"})
        return httpx.Response(404, json={"error": {"message": "?"}})

    ig, calls = make(h)
    req = PublishRequest(
        format="post",
        media=[{"kind": "image", "url": "https://x/1.jpg"}],
        caption="Merhaba",
        alt_text="bir çanta",
        first_comment="#a",
    )
    r = ig.publish(ACC, req)
    assert (r.remote_id, r.permalink) == ("M1", "https://instagram.com/p/x")
    create = calls[0]
    assert (
        create[1] == "/v25.0/1784/media"
        and create[2]["image_url"] == "https://x/1.jpg"
        and create[2]["alt_text"] == "bir çanta"
    )
    assert any(c[1].endswith("/media_publish") and c[2]["creation_id"] == "C1" for c in calls)


def test_video_still_processing_returns_pending():
    def h(req, calls):
        if req.url.path.endswith("/media"):
            return httpx.Response(200, json={"id": "C2"})
        return httpx.Response(200, json={"status_code": "IN_PROGRESS"})

    ig, calls = make(h)
    r = ig.publish(ACC, PublishRequest(format="reel", media=[{"kind": "video", "url": "https://x/v.mp4"}], caption="x"))
    assert r.pending == "C2" and not r.remote_id
    assert calls[0][2]["media_type"] == "REELS"


def test_carousel_creates_children_first():
    ids = iter(["A", "B", "P"])

    def h(req, calls):
        p = req.url.path
        if p.endswith("/1784/media"):
            return httpx.Response(200, json={"id": next(ids)})
        if p.endswith("/media_publish"):
            return httpx.Response(200, json={"id": "M"})
        return httpx.Response(200, json={"status_code": "FINISHED", "permalink": ""})

    ig, calls = make(h)
    media = [{"kind": "image", "url": "https://x/1.jpg"}, {"kind": "image", "url": "https://x/2.jpg"}]
    ig.publish(ACC, PublishRequest(format="carousel", media=media, caption="x"))
    creates = [c for c in calls if c[1].endswith("/1784/media")]
    assert creates[0][2]["is_carousel_item"] == "true"
    assert creates[2][2]["media_type"] == "CAROUSEL" and creates[2][2]["children"] == "A,B"


def test_errors_are_classified():
    def auth(req, calls):
        return httpx.Response(400, json={"error": {"code": 190, "message": "expired"}})

    ig, _ = make(auth)
    with pytest.raises(ProviderError) as e:
        ig.profile(ACC)
    assert e.value.code == "auth" and not e.value.retry

    def limit(req, calls):
        return httpx.Response(400, json={"error": {"code": 4, "message": "rate"}})

    ig, _ = make(limit)
    with pytest.raises(ProviderError) as e:
        ig.quota(ACC)
    assert e.value.retry


def test_insights_mapping_and_fallback():
    def h(req, calls):
        metric = req.url.params.get("metric", "")
        if "follows" in metric:
            return httpx.Response(400, json={"error": {"code": 100, "message": "bad metric"}})
        data = [{"name": n, "values": [{"value": i + 1}]} for i, n in enumerate(metric.split(","))]
        return httpx.Response(200, json={"data": data})

    ig, _ = make(h)
    m = ig.insights(ACC, "M1", "post", 0)
    assert m == {"reach": 1, "likes": 2, "comments": 3, "saves": 4, "shares": 5}


def test_comments_and_reply():
    def h(req, calls):
        if req.method == "GET":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "c1", "text": "Fiyat?", "username": "ayse", "timestamp": "2026-11-20T10:00:00+0000"}
                    ]
                },
            )
        return httpx.Response(200, json={"id": "r1"})

    ig, calls = make(h)
    cs = ig.comments(ACC, "M1", 0)
    assert cs[0]["remote_id"] == "c1" and cs[0]["ts"] > 0
    assert ig.reply(ACC, "c1", "Merhaba") == "r1"
    assert calls[-1][1] == "/v25.0/c1/replies" and calls[-1][2]["message"] == "Merhaba"
    _ = json
