"""HTTP API and web panel."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

from . import __version__, ads, analytics, auth_ig, compliance, content, inbox, planner, scheduler
from .brand import SECTORS, Brand, bio_suggestions, load_brand, save_brand
from .clock import hour as local_hour
from .config import Settings
from .db import Store
from .llm import make_chat
from .mediainfo import image_size, video_info
from .providers import ProviderError, get_provider

STATIC = Path(__file__).parent / "static"
IN_BROWSER = sys.platform == "emscripten"
MAX_UPLOAD = 100 * 1024 * 1024
ALLOWED = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
}
EDITABLE = {
    "caption",
    "hashtags",
    "alt_text",
    "first_comment",
    "story_text",
    "reel_hook",
    "cover_ms",
    "lang",
    "ai_label",
    "sponsored",
    "scheduled_at",
    "media_ids",
    "format",
    "pillar",
    "account_id",
}


class PostCreate(BaseModel):
    media_ids: list[int] = Field(min_length=1, max_length=10)
    format: Literal["post", "carousel", "reel", "story"] = "post"
    pillar: str = "urun"
    lang: str | None = None
    scheduled_at: float | None = None
    sponsored: bool = False
    ai_label: bool | None = None
    occasion: str | None = None


class PostPatch(BaseModel):
    caption: str | None = None
    hashtags: list[str] | None = None
    alt_text: str | None = None
    first_comment: str | None = None
    story_text: str | None = None
    reel_hook: str | None = None
    cover_ms: int | None = None
    lang: str | None = None
    ai_label: bool | None = None
    sponsored: bool | None = None
    scheduled_at: float | None = None
    media_ids: list[int] | None = None
    format: Literal["post", "carousel", "reel", "story"] | None = None
    pillar: str | None = None


class Regen(BaseModel):
    pillar: str | None = None
    format: Literal["post", "carousel", "reel", "story"] | None = None
    lang: str | None = None


class PlanReq(BaseModel):
    start: str | None = None  # YYYY-MM-DD, local
    seed: int | None = None


class MediaPatch(BaseModel):
    title: str | None = None
    notes: str | None = None
    tags: list[str] | None = None


class CommentPatch(BaseModel):
    reply_draft: str | None = None
    status: Literal["open", "ignored", "spam", "replied"] | None = None


class Bulk(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=200)
    action: Literal["approve", "reject", "delete", "pending"]


class Login(BaseModel):
    password: str


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    store = Store(settings.db_path)
    secret = store.get("secret")
    if not secret:
        secret = secrets.token_hex(32)
        store.put("secret", secret)
    chat = make_chat(settings) if not IN_BROWSER else None

    def provider_for_mode():  # noqa: ANN202
        if settings.mode == "instagram":
            return get_provider("instagram", settings)
        from .providers.demo import DemoProvider

        return DemoProvider(settings.timezone)

    provider = provider_for_mode()

    def media_url(m: dict[str, Any]) -> str:
        """A public, unguessable URL that Instagram's servers can download the file from."""
        sig = hmac.new(secret.encode(), f"m{m['id']}".encode(), hashlib.sha256).hexdigest()[:20]
        ext = Path(m["filename"]).suffix or ".jpg"
        return f"{settings.public_url}/p/{m['id']}-{sig}{ext}"

    def run_tick(force: bool = False) -> dict[str, Any]:
        return scheduler.tick(store, provider, media_url, force=force)

    if settings.mode == "demo":
        from .demo_seed import seed

        seed(store, settings.media_dir, settings.timezone)

    runner = scheduler.Runner(run_tick, interval=30)

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # noqa: ANN202
        if not IN_BROWSER:
            runner.start()
        yield
        runner.stop()

    app = FastAPI(
        title="Tellal", version=__version__, lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json"
    )
    app.state.store, app.state.settings, app.state.provider = store, settings, provider
    app.state.tick = run_tick

    # ------------------------------------------------------------------ auth
    def session_token() -> str:
        return hmac.new(secret.encode(), b"session:" + settings.admin_password.encode(), hashlib.sha256).hexdigest()

    @app.middleware("http")
    async def guard(request: Request, call_next):  # noqa: ANN001, ANN202
        p = request.url.path
        protected = (
            settings.admin_password
            and (p.startswith("/api/") or p.startswith("/media/"))
            and p not in {"/api/login", "/api/health"}
        )
        if protected and not hmac.compare_digest(request.cookies.get("tellal_session", ""), session_token()):
            return JSONResponse({"detail": "login"}, status_code=401)
        return await call_next(request)

    @app.post("/api/login")
    def login(body: Login) -> Response:
        if not settings.admin_password or not hmac.compare_digest(body.password, settings.admin_password):
            time.sleep(0.5)
            raise HTTPException(401, "Şifre yanlış.")
        r = JSONResponse({"ok": True})
        r.set_cookie(
            "tellal_session",
            session_token(),
            httponly=True,
            samesite="lax",
            max_age=30 * 86400,
            secure=settings.public_url.startswith("https"),
        )
        return r

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "version": __version__}

    # ------------------------------------------------------------------ helpers
    def lang_of(request: Request) -> str:
        q = request.query_params.get("lang")
        if q in {"tr", "en"}:
            return q
        return "en" if request.headers.get("accept-language", "tr").lower().startswith("en") else "tr"

    def media_rows(ids: list[int]) -> list[dict[str, Any] | None]:
        return [store.media(i) for i in ids]

    def findings(p: dict[str, Any], lang: str) -> list[dict[str, str]]:
        return compliance.check_post(
            p,
            media_rows(p["media_ids"]),
            load_brand(store),
            lang=lang,
            now=time.time(),
            tz_hour=lambda ts: local_hour(ts, settings.timezone),
            has_account=bool(store.accounts()),
        )

    def post_out(p: dict[str, Any], lang: str, full: bool = False) -> dict[str, Any]:
        p = dict(p)
        p.pop("token", None)
        f = findings(p, lang) if p["status"] in {"draft", "pending", "approved", "failed"} else []
        p["blocked"] = compliance.blocking(f)
        p["counts"] = {lvl: sum(1 for x in f if x["level"] == lvl) for lvl in ("error", "warn", "info")}
        if full:
            p["findings"] = f
            p["media"] = [m for m in media_rows(p["media_ids"]) if m]
            p["rates"] = analytics.rates(p) if p.get("reach") else None
            p["comments_list"] = [c for c in store.comments() if c["post_id"] == p["id"]]
            brand = load_brand(store)
            first = p["media"][0] if p["media"] else {}
            ideas = content.build_hashtags(
                brand,
                first.get("title") or "",
                p.get("pillar") or "urun",
                extra=[content.hashtag_slug(t) for t in (first.get("tags") or [])],
            )
            ideas += [content.hashtag_slug(str(t)) for t in SECTORS.get(brand.sector, SECTORS["diger"])["tags"]]
            p["tag_ideas"] = [t for t in dict.fromkeys(ideas) if t and t not in (p.get("hashtags") or [])][:6]
        return p

    def must_post(pid: int) -> dict[str, Any]:
        p = store.post(pid)
        if not p:
            raise HTTPException(404, "Gönderi bulunamadı.")
        return p

    # ------------------------------------------------------------------ overview
    @app.get("/api/state")
    def state(request: Request) -> dict[str, Any]:
        lang = lang_of(request)
        now = time.time()
        posts = store.posts()
        accs = [{k: v for k, v in a.items() if k != "token"} for a in store.accounts()]
        upcoming = [
            p for p in posts if p["status"] in {"approved", "publishing"} and (p.get("scheduled_at") or 0) >= now - 3600
        ]
        from datetime import datetime

        from .clock import tz

        today = datetime.now(tz(settings.timezone)).date()
        brand = load_brand(store)
        return {
            "version": __version__,
            "mode": settings.mode,
            "in_browser": IN_BROWSER,
            "timezone": settings.timezone,
            "public_url": settings.public_url,
            "llm": bool(chat),
            "ig_configured": bool(settings.ig_app_id and settings.ig_app_secret),
            "login_required": bool(settings.admin_password),
            "brand": brand.model_dump(),
            "accounts": accs,
            "counts": {
                "pending": sum(1 for p in posts if p["status"] == "pending"),
                "approved": len(upcoming),
                "failed": sum(1 for p in posts if p["status"] == "failed"),
                "comments": len(store.comments("open")),
                "media": len(store.media_list()),
                "published_7d": sum(
                    1 for p in posts if p["status"] == "published" and (p.get("published_at") or 0) >= now - 7 * 86400
                ),
            },
            "next": [post_out(p, lang) for p in upcoming[:5]],
            "occasions": content.upcoming_occasions(today, 30),
            "best_slots": analytics.best_slots(
                posts, settings.timezone, (brand.rhythm.quiet_start, brand.rhythm.quiet_end)
            ),
            "events": store.events(15),
        }

    # ------------------------------------------------------------------ brand
    @app.get("/api/brand")
    def get_brand() -> dict[str, Any]:
        return {
            "brand": load_brand(store).model_dump(),
            "sectors": {k: v["label"] for k, v in SECTORS.items()},
            "bios": bio_suggestions(load_brand(store)),
        }

    @app.put("/api/brand")
    def put_brand(b: Brand) -> dict[str, Any]:
        b.brand_hashtag = content.hashtag_slug(b.brand_hashtag) if b.brand_hashtag else ""
        save_brand(store, b)
        store.log("brand", "Marka profili güncellendi.")
        return {"brand": b.model_dump(), "bios": bio_suggestions(b)}

    # ------------------------------------------------------------------ media
    @app.get("/api/media")
    def list_media() -> list[dict[str, Any]]:
        usage = store.media_usage()
        return [{**m, "used": usage.get(m["id"], 0)} for m in store.media_list()]

    @app.post("/api/media")
    async def upload(
        file: UploadFile = File(...),
        title: str = Form(""),
        notes: str = Form(""),
        tags: str = Form(""),
        width: int = Form(0),
        height: int = Form(0),
        duration: float = Form(0),
        parent_id: int = Form(0),
        poster: UploadFile | None = File(None),
    ) -> dict[str, Any]:
        data = await file.read()
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "Dosya 100 MB'tan büyük.")
        mime = (file.content_type or "").split(";")[0]
        if mime not in ALLOWED:
            raise HTTPException(415, "Yalnızca JPEG, PNG, WebP fotoğraf ve MP4/MOV video yüklenebilir.")
        kind = "video" if mime.startswith("video/") else "image"
        if kind == "image":
            size = image_size(data)
            if not size:
                raise HTTPException(400, "Görsel okunamadı.")
            width, height = size
        else:
            vi = video_info(data)
            width = int(vi.get("width") or width)
            height = int(vi.get("height") or height)
            duration = float(vi.get("duration") or duration)
        mid = store.add_media(
            kind=kind,
            filename="",
            mime=mime,
            width=width,
            height=height,
            duration=duration or None,
            size=len(data),
            title=title.strip()[:120] or Path(file.filename or "").stem[:120],
            notes=notes.strip()[:2000],
            tags=[t.strip().lstrip("#") for t in tags.split(",") if t.strip()][:10],
            parent_id=parent_id or None,
        )
        name = f"{mid}{ALLOWED[mime]}"
        (settings.media_dir / name).write_bytes(data)
        store.update_media(mid, filename=name)
        if kind == "video" and poster is not None:
            pdata = await poster.read()
            if pdata[:2] == b"\xff\xd8" and len(pdata) < 5 * 1024 * 1024:
                (settings.media_dir / f"{mid}.poster.jpg").write_bytes(pdata)
        return {**(store.media(mid) or {}), "used": 0}

    @app.patch("/api/media/{mid}")
    def patch_media(mid: int, body: MediaPatch) -> dict[str, Any]:
        if not store.media(mid):
            raise HTTPException(404, "Medya bulunamadı.")
        store.update_media(mid, **body.model_dump(exclude_none=True))
        return store.media(mid) or {}

    @app.delete("/api/media/{mid}")
    def delete_media(mid: int) -> dict[str, Any]:
        m = store.media(mid)
        if not m:
            raise HTTPException(404, "Medya bulunamadı.")
        busy = [p["id"] for p in store.posts("pending,approved,publishing") if mid in p["media_ids"]]
        if busy:
            raise HTTPException(409, f"Bu medya {len(busy)} planlı gönderide kullanılıyor; önce onları değiştirin.")
        store.delete_media(mid)
        (settings.media_dir / m["filename"]).unlink(missing_ok=True)
        (settings.media_dir / f"{mid}.poster.jpg").unlink(missing_ok=True)
        return {"ok": True}

    def send_media(m: dict[str, Any] | None) -> Response:
        if not m:
            raise HTTPException(404)
        path = settings.media_dir / m["filename"]
        if not path.is_file():
            raise HTTPException(404)
        if IN_BROWSER:
            return Response(
                path.read_bytes(), media_type=m["mime"], headers={"cache-control": "private, max-age=86400"}
            )
        return FileResponse(path, media_type=m["mime"], headers={"cache-control": "private, max-age=86400"})

    @app.get("/media/{mid}")
    def get_media(mid: int) -> Response:
        return send_media(store.media(mid))

    @app.get("/media/{mid}/poster")
    def get_poster(mid: int) -> Response:
        path = settings.media_dir / f"{mid}.poster.jpg"
        if not path.is_file():
            raise HTTPException(404)
        return Response(path.read_bytes(), media_type="image/jpeg", headers={"cache-control": "private, max-age=86400"})

    @app.get("/p/{token}")
    def public_media(token: str) -> Response:
        """For Instagram's servers: unguessable URL, no login."""
        base = token.rsplit(".", 1)[0]
        try:
            mid_s, sig = base.split("-", 1)
            mid = int(mid_s)
        except ValueError:
            raise HTTPException(404) from None
        good = hmac.new(secret.encode(), f"m{mid}".encode(), hashlib.sha256).hexdigest()[:20]
        if not hmac.compare_digest(good, sig):
            raise HTTPException(404)
        return send_media(store.media(mid))

    # ------------------------------------------------------------------ posts
    @app.get("/api/posts")
    def list_posts(
        request: Request, status: str | None = None, start: float | None = None, end: float | None = None
    ) -> list[dict[str, Any]]:
        lang = lang_of(request)
        return [post_out(p, lang) for p in store.posts(status, start, end)]

    @app.get("/api/posts/{pid}")
    def get_post(pid: int, request: Request) -> dict[str, Any]:
        return post_out(must_post(pid), lang_of(request), full=True)

    @app.post("/api/posts")
    def create_post(body: PostCreate, request: Request) -> dict[str, Any]:
        brand = load_brand(store)
        media = [m for m in media_rows(body.media_ids) if m]
        if len(media) != len(body.media_ids):
            raise HTTPException(400, "Seçilen medyalardan biri yok.")
        fmt = body.format
        if fmt != "carousel" and len(media) > 1:
            fmt = "carousel"
        ai = brand.ai_label_default if body.ai_label is None else body.ai_label
        lang = body.lang or brand.primary_lang
        seed = secrets.randbelow(10_000)
        if chat:
            d = content.llm_generate(
                brand, media, fmt, body.pillar, lang, body.occasion, seed, body.sponsored, ai, chat
            )
        else:
            d = content.generate(brand, media, fmt, body.pillar, lang, body.occasion, seed, body.sponsored, ai)
        pid = store.add_post(
            format=fmt,
            media_ids=body.media_ids,
            caption=d.caption,
            hashtags=d.hashtags,
            alt_text=d.alt_text,
            story_text="\n".join(d.story_frames),
            reel_hook=d.reel_hook,
            lang=d.lang,
            ai_label=ai,
            sponsored=body.sponsored,
            status="pending",
            scheduled_at=body.scheduled_at,
            source="manual",
            pillar=body.pillar,
            rationale=d.rationale,
            extra={
                "story_frames": d.story_frames,
                "sticker": d.sticker,
                "reel_script": d.reel_script,
                "carousel_slides": d.carousel_slides,
                "engine": d.engine,
                "seed": seed,
                "occasion": body.occasion,
            },
        )
        store.log("draft", "Yeni taslak hazırlandı.", pid)
        return post_out(must_post(pid), lang_of(request), full=True)

    @app.patch("/api/posts/{pid}")
    def patch_post(pid: int, body: PostPatch, request: Request) -> dict[str, Any]:
        p = must_post(pid)
        if p["status"] in {"published", "publishing"}:
            raise HTTPException(409, "Paylaşılmış gönderi düzenlenemez.")
        data = {k: v for k, v in body.model_dump(exclude_unset=True).items() if k in EDITABLE}
        if "hashtags" in data and data["hashtags"] is not None:
            data["hashtags"] = list(dict.fromkeys(t for t in (content.hashtag_slug(x) for x in data["hashtags"]) if t))
        if "story_text" in data and data["story_text"] is not None:
            data["extra"] = {
                **(p.get("extra") or {}),
                "story_frames": [x for x in data["story_text"].split("\n") if x.strip()],
            }
        # Any edit after approval sends it back for a final look.
        if p["status"] == "approved" and set(data) - {"scheduled_at"}:
            data["status"] = "pending"
        if p["status"] == "failed":
            data.update(status="pending", error=None, attempts=0, next_try=None)
        store.update_post(pid, **data)
        return post_out(must_post(pid), lang_of(request), full=True)

    @app.post("/api/posts/{pid}/approve")
    def approve(pid: int, request: Request) -> dict[str, Any]:
        lang = lang_of(request)
        p = must_post(pid)
        if p["status"] not in {"pending", "draft", "failed"}:
            raise HTTPException(409, "Bu gönderi onay beklemiyor.")
        f = findings(p, lang)
        if compliance.blocking(f):
            raise HTTPException(
                422, {"message": "Önce hataları düzeltin." if lang == "tr" else "Fix the errors first.", "findings": f}
            )
        when = p.get("scheduled_at") or time.time() + 300
        store.update_post(pid, status="approved", scheduled_at=when, error=None, attempts=0, next_try=None)
        store.log("approved", "Onaylandı, zamanı gelince paylaşılacak.", pid)
        return post_out(must_post(pid), lang, full=True)

    @app.post("/api/posts/{pid}/publish-now")
    def publish_now(pid: int, request: Request) -> dict[str, Any]:
        lang = lang_of(request)
        p = must_post(pid)
        if p["status"] in {"pending", "draft", "failed"}:
            approve(pid, request)
        elif p["status"] != "approved":
            raise HTTPException(409, "Bu gönderi paylaşılamaz.")
        store.update_post(pid, scheduled_at=time.time() - 1, next_try=None)
        scheduler.publish_one(store, must_post(pid), provider, media_url)
        return post_out(must_post(pid), lang, full=True)

    @app.post("/api/posts/{pid}/reject")
    def reject(pid: int, request: Request) -> dict[str, Any]:
        p = must_post(pid)
        if p["status"] in {"published", "publishing"}:
            raise HTTPException(409, "Paylaşılmış gönderi geri alınamaz.")
        store.update_post(pid, status="rejected")
        store.log("rejected", "Reddedildi.", pid)
        return post_out(must_post(pid), lang_of(request))

    @app.post("/api/posts/{pid}/unapprove")
    def unapprove(pid: int, request: Request) -> dict[str, Any]:
        p = must_post(pid)
        if p["status"] not in {"approved", "rejected", "failed"}:
            raise HTTPException(409, "Geri alınacak bir onay yok.")
        store.update_post(pid, status="pending", next_try=None)
        return post_out(must_post(pid), lang_of(request), full=True)

    @app.post("/api/posts/{pid}/regenerate")
    def regen(pid: int, body: Regen, request: Request) -> dict[str, Any]:
        p = planner.regenerate(store, load_brand(store), pid, chat, body.pillar, body.format, body.lang)
        if not p:
            raise HTTPException(409, "Bu gönderi yeniden yazılamaz.")
        return post_out(p, lang_of(request), full=True)

    @app.post("/api/posts/{pid}/duplicate")
    def duplicate(pid: int, request: Request) -> dict[str, Any]:
        p = must_post(pid)
        keep = {
            k: p[k]
            for k in [
                "format",
                "media_ids",
                "caption",
                "hashtags",
                "alt_text",
                "first_comment",
                "story_text",
                "reel_hook",
                "lang",
                "ai_label",
                "sponsored",
                "pillar",
                "rationale",
                "extra",
                "cover_ms",
            ]
        }
        new = store.add_post(**keep, status="pending", source="copy")
        return post_out(must_post(new), lang_of(request), full=True)

    @app.delete("/api/posts/{pid}")
    def delete_post(pid: int) -> dict[str, Any]:
        p = must_post(pid)
        if p["status"] == "publishing":
            raise HTTPException(409, "Şu an paylaşılıyor.")
        store.delete_post(pid)
        return {"ok": True}

    @app.post("/api/posts/bulk")
    def bulk(body: Bulk, request: Request) -> dict[str, Any]:
        lang = lang_of(request)
        done, skipped = 0, 0
        for pid in body.ids:
            p = store.post(pid)
            if not p or p["status"] in {"published", "publishing"}:
                skipped += 1
                continue
            if body.action == "approve":
                if compliance.blocking(findings(p, lang)) or p["status"] not in {"pending", "draft", "failed"}:
                    skipped += 1
                    continue
                store.update_post(
                    pid, status="approved", scheduled_at=p.get("scheduled_at") or time.time() + 300, next_try=None
                )
            elif body.action == "reject":
                store.update_post(pid, status="rejected")
            elif body.action == "pending":
                store.update_post(pid, status="pending", next_try=None)
            else:
                store.delete_post(pid)
            done += 1
        if done:
            store.log("bulk", f"{done} içerik: {body.action}.")
        return {"done": done, "skipped": skipped}

    @app.get("/api/export")
    def export() -> Response:
        """Everything except media files and tokens, as one JSON file (backup or moving to another server)."""
        import json as _json

        data = {
            "app": "tellal",
            "version": __version__,
            "exported_at": time.time(),
            "brand": load_brand(store).model_dump(),
            "accounts": [{k: v for k, v in a.items() if k != "token"} for a in store.accounts()],
            "media": store.media_list(),
            "posts": store.posts(),
            "comments": store.comments(),
            "events": store.events(1000),
        }
        body = _json.dumps(data, ensure_ascii=False, indent=1, default=str)
        stamp = time.strftime("%Y%m%d")
        return Response(
            body,
            media_type="application/json",
            headers={"content-disposition": f'attachment; filename="tellal-yedek-{stamp}.json"'},
        )

    @app.post("/api/posts/approve-all")
    def approve_all(request: Request) -> dict[str, Any]:
        lang = lang_of(request)
        ok, skipped = 0, 0
        for p in store.posts("pending"):
            if compliance.blocking(findings(p, lang)) or not p.get("scheduled_at"):
                skipped += 1
                continue
            store.update_post(p["id"], status="approved", next_try=None)
            ok += 1
        if ok:
            store.log("approved", f"{ok} içerik toplu onaylandı.")
        return {"approved": ok, "skipped": skipped}

    # ------------------------------------------------------------------ plan, analysis, ads
    @app.post("/api/plan")
    def plan(body: PlanReq, request: Request) -> dict[str, Any]:
        from datetime import datetime

        from .clock import tz

        start = None
        if body.start:
            start = datetime.fromisoformat(body.start).replace(
                tzinfo=tz(settings.timezone), hour=0, minute=0, second=0, microsecond=0
            )
        if not store.media_list():
            raise HTTPException(400, "Önce kütüphaneye fotoğraf veya video ekleyin.")
        return planner.plan_week(store, load_brand(store), settings.timezone, start, chat, lang_of(request), body.seed)

    @app.get("/api/analytics")
    def get_analytics(request: Request, days: int = 30) -> dict[str, Any]:
        return analytics.summary(store.posts(), settings.timezone, days=max(7, min(days, 365)), lang=lang_of(request))

    @app.get("/api/ads")
    def get_ads(request: Request) -> dict[str, Any]:
        return ads.candidates(store.posts(), load_brand(store), lang=lang_of(request))

    @app.get("/api/ads/estimate")
    def ad_estimate(format: str = "reel", daily: float = 200, days: int = 5) -> dict[str, Any]:  # noqa: A002
        return ads.estimate(format, max(20, min(daily, 100_000)), max(1, min(days, 60)))

    # ------------------------------------------------------------------ comments
    @app.get("/api/comments")
    def list_comments(status: str | None = None) -> list[dict[str, Any]]:
        out = []
        cache: dict[int, dict[str, Any] | None] = {}
        for c in store.comments(status):
            pid = c.get("post_id")
            if pid not in cache:
                cache[pid] = store.post(pid) if pid else None
            p = cache[pid]
            out.append(
                {
                    **c,
                    "label": inbox.LABELS.get(c.get("intent") or "diger", ""),
                    "post": {
                        "id": p["id"],
                        "caption": (p.get("caption") or "")[:80],
                        "media_ids": p["media_ids"],
                        "permalink": p.get("permalink"),
                    }
                    if p
                    else None,
                }
            )
        return out

    @app.patch("/api/comments/{cid}")
    def patch_comment(cid: int, body: CommentPatch) -> dict[str, Any]:
        if not store.comment(cid):
            raise HTTPException(404)
        store.update_comment(cid, **body.model_dump(exclude_none=True))
        return store.comment(cid) or {}

    @app.post("/api/comments/{cid}/send")
    def send_reply(cid: int) -> dict[str, Any]:
        c = store.comment(cid)
        if not c:
            raise HTTPException(404)
        text = (c.get("reply_draft") or "").strip()
        if not text:
            raise HTTPException(400, "Yanıt boş.")
        p = store.post(c["post_id"]) if c.get("post_id") else None
        acc = (store.account(p["account_id"]) if p and p.get("account_id") else None) or (store.accounts() or [None])[0]
        if not acc:
            raise HTTPException(400, "Bağlı hesap yok.")
        try:
            provider.reply(acc, c["remote_id"], text)
        except ProviderError as e:
            raise HTTPException(502, str(e)) from e
        store.update_comment(cid, status="replied", reply_text=text)
        store.log("reply", f"@{c.get('username')} yorumuna yanıt gönderildi.", c.get("post_id"))
        return store.comment(cid) or {}

    # ------------------------------------------------------------------ scheduler
    @app.post("/api/scheduler/tick")
    def tick(force: bool = False) -> dict[str, Any]:
        return run_tick(force)

    @app.get("/api/events")
    def events(limit: int = 50) -> list[dict[str, Any]]:
        return store.events(min(limit, 200))

    # ------------------------------------------------------------------ accounts
    @app.get("/auth/instagram/start")
    def ig_start() -> Response:
        if not (settings.ig_app_id and settings.ig_app_secret):
            raise HTTPException(
                400, "TELLAL_IG_APP_ID ve TELLAL_IG_APP_SECRET ayarlanmamış (README: Instagram bağlantısı)."
            )
        return RedirectResponse(auth_ig.authorize_url(settings, auth_ig.make_state(secret)))

    @app.get("/auth/instagram/callback")
    def ig_callback(code: str = "", state: str = "", error_description: str = "") -> Response:
        if error_description:
            return RedirectResponse(f"/#/ayarlar?hata={error_description[:200]}")
        if not auth_ig.check_state(secret, state):
            raise HTTPException(400, "Geçersiz ya da süresi dolmuş istek, yeniden deneyin.")
        try:
            uid, token, exp = auth_ig.exchange_code(settings, code)
            from .providers.instagram import InstagramProvider

            prof = InstagramProvider(settings).profile({"token": token, "remote_id": uid})
        except (ValueError, ProviderError) as e:
            return RedirectResponse(f"/#/ayarlar?hata={str(e)[:200]}")
        store.upsert_account(
            "instagram",
            prof["remote_id"] or uid,
            username=prof["username"],
            name=prof["name"],
            picture=prof["picture"],
            followers=prof["followers"],
            token=token,
            token_expires=exp,
        )
        store.log("account", f"@{prof['username']} bağlandı.")
        return RedirectResponse("/#/ayarlar?baglandi=1")

    @app.post("/api/accounts/{aid}/refresh")
    def refresh_account(aid: int) -> dict[str, Any]:
        a = store.account(aid)
        if not a:
            raise HTTPException(404)
        try:
            prof = provider.profile(a)
        except ProviderError as e:
            raise HTTPException(502, str(e)) from e
        store.update_account(
            aid,
            username=prof["username"] or a["username"],
            name=prof["name"],
            followers=prof["followers"],
            picture=prof.get("picture") or a.get("picture"),
        )
        return {k: v for k, v in (store.account(aid) or {}).items() if k != "token"}

    @app.delete("/api/accounts/{aid}")
    def remove_account(aid: int) -> dict[str, Any]:
        store.delete_account(aid)
        return {"ok": True}

    @app.post("/api/demo/reset")
    def demo_reset() -> dict[str, Any]:
        if settings.mode != "demo":
            raise HTTPException(403, "Yalnızca demo modunda.")
        from .demo_seed import seed

        for f in settings.media_dir.glob("*"):
            f.unlink()
        with store._lock, store._con() as c:  # noqa: SLF001
            for t in ["accounts", "media", "posts", "insights", "comments", "events"]:
                c.execute(f"DELETE FROM {t}")
            c.execute("DELETE FROM kv WHERE key IN ('seeded','brand','last_refresh')")
            c.execute("DELETE FROM sqlite_sequence")
        return seed(store, settings.media_dir, settings.timezone)

    # ------------------------------------------------------------------ web panel
    def static_file(name: str, mime: str, cache: str = "no-cache") -> Response:
        path = STATIC / name
        if not path.is_file():
            raise HTTPException(404)
        return Response(path.read_bytes(), media_type=mime, headers={"cache-control": cache})

    @app.get("/fonts/{name}", include_in_schema=False)
    def font(name: str) -> Response:
        if name.endswith(".woff2") and "/" not in name and ".." not in name:
            path = STATIC / "fonts" / name
            if path.is_file():
                return Response(
                    path.read_bytes(), media_type="font/woff2", headers={"cache-control": "public, max-age=31536000"}
                )
        raise HTTPException(404)

    @app.get("/", response_class=HTMLResponse)
    def index() -> Response:
        return static_file("index.html", "text/html; charset=utf-8")

    for name, mime in [
        ("app.js", "text/javascript"),
        ("app.css", "text/css"),
        ("appkit.js", "text/javascript"),
        ("sw.js", "text/javascript"),
        ("manifest.webmanifest", "application/manifest+json"),
        ("icon-192.png", "image/png"),
        ("icon-512.png", "image/png"),
        ("maskable-512.png", "image/png"),
        ("apple-touch-icon.png", "image/png"),
        ("icon.svg", "image/svg+xml"),
    ]:
        app.add_api_route(
            f"/{name}", (lambda n=name, m=mime: static_file(n, m)), methods=["GET"], include_in_schema=False
        )

    return app


_APP: FastAPI | None = None


def __getattr__(name: str):  # noqa: ANN202 - the app is built on first use, so importing has no side effects
    global _APP
    if name == "app":
        if _APP is None:
            _APP = create_app()
        return _APP
    raise AttributeError(name)
