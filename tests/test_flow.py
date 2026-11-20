import time
from datetime import datetime, timedelta

from tellal import planner, scheduler
from tellal.brand import load_brand
from tellal.clock import tz
from tellal.providers import ProviderError, PublishRequest, PublishResult
from tellal.providers.demo import DemoProvider


def test_demo_seed_fills_every_screen(client):
    st = client.get("/api/state").json()
    assert st["mode"] == "demo" and st["counts"]["pending"] > 0 and st["counts"]["media"] >= 10
    a = client.get("/api/analytics").json()
    assert a["totals"]["posts"] > 10 and a["advice"] and len(a["heatmap"]) == 7
    assert client.get("/api/ads").json()["items"]
    assert client.get("/api/comments?status=open").json()


def test_approve_requires_a_clean_post(client):
    m = client.get("/api/media").json()
    img = next(x for x in m if x["kind"] == "image")
    p = client.post("/api/posts", json={"media_ids": [img["id"]], "format": "post", "pillar": "kampanya"}).json()
    assert p["blocked"]  # [placeholder] for the offer details
    r = client.post(f"/api/posts/{p['id']}/approve")
    assert r.status_code == 422
    fixed = p["caption"].split("[")[0] + "Bu hafta tüm cüzdanlarda kargo ücretsiz."
    client.patch(f"/api/posts/{p['id']}", json={"caption": fixed, "scheduled_at": time.time() + 3600})
    assert client.post(f"/api/posts/{p['id']}/approve").json()["status"] == "approved"
    # editing after approval sends it back for review
    assert client.patch(f"/api/posts/{p['id']}", json={"caption": fixed + " !"}).json()["status"] == "pending"


def test_publish_now_in_demo(client):
    m = client.get("/api/media").json()
    img = next(x for x in m if x["kind"] == "image")
    p = client.post("/api/posts", json={"media_ids": [img["id"]], "format": "post", "pillar": "urun"}).json()
    r = client.post(f"/api/posts/{p['id']}/publish-now").json()
    assert r["status"] == "published" and r["remote_id"].startswith("demo_")


def test_upload_reads_real_dimensions(client):
    from importlib import resources

    data = (resources.files("tellal") / "demo_media" / "taba-cuzdan.jpg").read_bytes()
    r = client.post(
        "/api/media",
        files={"file": ("x.jpg", data, "image/jpeg")},
        data={"title": "Cüzdan", "width": "1", "height": "1"},
    )
    assert r.status_code == 200 and (r.json()["width"], r.json()["height"]) == (864, 1080)
    assert client.get(f"/media/{r.json()['id']}").content == data
    bad = client.post("/api/media", files={"file": ("x.gif", b"GIF89a", "image/gif")})
    assert bad.status_code == 415


def test_public_media_url_is_signed(client):
    mid = client.get("/api/media").json()[0]["id"]
    assert client.get(f"/p/{mid}-0000000000.jpg").status_code == 404


def test_plan_fills_week_and_respects_rhythm(client, settings):
    store = client.app.state.store
    start = (datetime.now(tz(settings.timezone)) + timedelta(days=14)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    r = planner.plan_week(store, load_brand(store), settings.timezone, start, seed=3)
    posts = [store.post(i) for i in r["created"]]
    rh = load_brand(store).rhythm
    feed = [p for p in posts if p["format"] in {"post", "carousel"}]
    reels = [p for p in posts if p["format"] == "reel"]
    assert len(feed) + len(reels) == rh.posts_per_week + rh.reels_per_week, r["notes"]
    assert all(p["status"] == "pending" and p["rationale"] for p in posts)
    # planning again doesn't double the week
    again = planner.plan_week(store, load_brand(store), settings.timezone, start, seed=4)
    assert len(again["created"]) == 0


class Flaky(DemoProvider):
    def __init__(self, fails):
        super().__init__()
        self.fails = fails

    def publish(self, account, req: PublishRequest) -> PublishResult:
        if self.fails:
            self.fails -= 1
            raise ProviderError("timeout", retry=True)
        return PublishResult(remote_id="ok1")


def test_scheduler_retries_then_publishes(client):
    store = client.app.state.store
    m = client.get("/api/media").json()
    img = next(x for x in m if x["kind"] == "image")
    p = client.post("/api/posts", json={"media_ids": [img["id"]], "format": "post", "pillar": "urun"}).json()
    client.post(f"/api/posts/{p['id']}/approve")
    store.update_post(p["id"], scheduled_at=time.time() - 10)
    prov = Flaky(fails=1)
    url = lambda m: "https://x/" + str(m["id"])  # noqa: E731
    now = time.time()
    scheduler.tick(store, prov, url, now=now)
    after = store.post(p["id"])
    assert after["status"] == "approved" and after["attempts"] == 1 and after["next_try"] > now
    scheduler.tick(store, prov, url, now=after["next_try"] + 1)
    assert store.post(p["id"])["status"] == "published"


def test_scheduler_never_publishes_pending(client):
    store = client.app.state.store
    for p in store.posts("pending"):
        store.update_post(p["id"], scheduled_at=time.time() - 10)
    scheduler.tick(store, DemoProvider(), lambda m: "https://x", now=time.time())
    assert all(p["status"] == "pending" for p in store.posts("pending"))
    assert store.posts("pending")


def test_login_guard(tmp_path):
    from fastapi.testclient import TestClient

    from tellal.api import create_app
    from tellal.config import Settings

    s = Settings(data_dir=tmp_path, mode="demo", llm_enabled=False, admin_password="gizli")
    with TestClient(create_app(s)) as c:
        assert c.get("/api/state").status_code == 401
        assert c.get("/").status_code == 200
        assert c.post("/api/login", json={"password": "yanlis"}).status_code == 401
        assert c.post("/api/login", json={"password": "gizli"}).status_code == 200
        assert c.get("/api/state").status_code == 200


def test_comment_reply_flow(client):
    c = client.get("/api/comments?status=open").json()[0]
    client.patch(f"/api/comments/{c['id']}", json={"reply_draft": "Teşekkürler!"})
    r = client.post(f"/api/comments/{c['id']}/send").json()
    assert r["status"] == "replied" and r["reply_text"] == "Teşekkürler!"


def test_video_posters_and_editor_helpers(client):
    media = client.get("/api/media").json()
    video = next(m for m in media if m["kind"] == "video")
    r = client.get(f"/media/{video['id']}/poster")
    assert r.status_code == 200 and r.content[:2] == b"\xff\xd8"
    st = client.get("/api/state").json()
    assert set(st["best_slots"]) == {str(d) for d in range(7)}
    pid = client.get("/api/posts?status=pending").json()[0]["id"]
    p = client.get(f"/api/posts/{pid}").json()
    assert all(t not in p["hashtags"] for t in p["tag_ideas"])


def test_fonts_are_served(client):
    r = client.get("/fonts/geist-latin-wght-normal.woff2")
    assert r.status_code == 200 and r.headers["content-type"] == "font/woff2"
    assert client.get("/fonts/..%2Fapp.js").status_code == 404


def test_bulk_actions_and_reschedule_keep_approval(client):
    pending = client.get("/api/posts?status=pending").json()
    ready = [p["id"] for p in pending if not p["blocked"]][:2]
    blocked = [p["id"] for p in pending if p["blocked"]][:1]
    r = client.post("/api/posts/bulk", json={"ids": ready + blocked, "action": "approve"}).json()
    assert r["done"] == len(ready) and r["skipped"] == len(blocked)
    pid = ready[0]
    p = client.patch(f"/api/posts/{pid}", json={"scheduled_at": time.time() + 3 * 86400}).json()
    assert p["status"] == "approved"  # moving a post doesn't need a second approval
    assert client.patch(f"/api/posts/{pid}", json={"caption": "Yeni metin."}).json()["status"] == "pending"
    assert client.post("/api/posts/bulk", json={"ids": [pid], "action": "delete"}).json()["done"] == 1
    assert client.get(f"/api/posts/{pid}").status_code == 404


def test_export_has_no_tokens(client):
    r = client.get("/api/export")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    data = r.json()
    assert data["posts"] and data["brand"]["name"]
    assert all("token" not in a for a in data["accounts"])


def test_analytics_series_lines_up(client):
    a = client.get("/api/analytics?days=30").json()
    s = a["series"]
    assert len(s["labels"]) == len(s["current"]) == len(s["previous"]) == 30
    assert sum(s["current"]) == a["totals"]["reach"]
