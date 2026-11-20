// Tellal web panel. Plain JavaScript, no build step. All API paths are relative, so the same page works
// under the Python server and in the in-browser build (served from a sub-folder).
(() => {
"use strict";

// ------------------------------------------------------------------ i18n
const DICT = {
  tr: {
    today: "Bugün", approve: "Onay", calendar: "Takvim", library: "Kütüphane", more: "Daha", analysis: "Analiz", ads: "Reklam",
    comments: "Yorumlar", brand: "Marka", settings: "Ayarlar",
    pending: "Onay bekliyor", approved: "Onaylandı", published: "Paylaşıldı", failed: "Hata", rejected: "Reddedildi", publishing: "Paylaşılıyor", draft: "Taslak",
    post: "Gönderi", carousel: "Kaydırmalı", reel: "Reels", story: "Hikâye",
    p_urun: "Ürün", p_surec: "Kamera arkası", p_ipucu: "İpucu", p_topluluk: "Soru / anket", p_kampanya: "Kampanya", p_kanit: "Müşteri yorumu",
    planWeek: "Haftayı planla", newPost: "Yeni içerik", approveAll: "Uygunları onayla", reject: "Reddet", edit: "Düzenle", ok: "Onayla",
    save: "Kaydet", cancel: "Vazgeç", del: "Sil", rewrite: "Yeniden yaz", publishNow: "Şimdi paylaş", duplicate: "Kopyala", close: "Kapat",
    caption: "Açıklama", hashtags: "Hashtagler", alt: "Alternatif metin", firstComment: "İlk yorum", when: "Paylaşım zamanı",
    sponsored: "İş birliği / reklam içeriği", aiLabel: "Yapay zekâ ile üretilmiş görsel var", why: "Neden böyle?", checks: "Kontroller",
    noPending: "Onay bekleyen içerik yok", noPendingT: "Haftayı planlayın; Tellal kütüphanenizden içerik hazırlayıp buraya getirir.",
    swipeHint: "Sağa kaydır: onayla · sola: reddet · dokun: düzenle",
    upload: "Fotoğraf / video ekle", uploadHint: "Kendi ürün fotoğraflarınız ve kısa dikey videolarınız. Tellal açıklamaları bunlardan ve yazdığınız notlardan üretir.",
    title: "Başlık (ürün adı)", notes: "Notlar", notesHint: "1–3 kısa cümle: malzeme, özellik, ölçü… Açıklama bundan yazılır. Uydurulmaz.", tags: "Etiketler",
    crop: "Kırpma", original: "Orijinal", suggested: "önerilen",
    reach: "Erişim", interactions: "Etkileşim", saves: "Kaydetme", shares: "Gönderilme", follows: "Takip", views: "Görüntülenme",
    loginT: "Giriş", password: "Şifre", login: "Giriş yap",
    sound: "Sesler", theme: "Tema", language: "Dil", auto: "Otomatik", light: "Açık", dark: "Koyu",
    copied: "Kopyalandı", saved: "Kaydedildi", error: "Bir sorun oldu",
    week: "Hafta", prev: "Önceki", next: "Sonraki", thisWeek: "Bu hafta",
  },
  en: {
    today: "Today", approve: "Review", calendar: "Calendar", library: "Library", more: "More", analysis: "Insights", ads: "Ads",
    comments: "Comments", brand: "Brand", settings: "Settings",
    pending: "To review", approved: "Approved", published: "Published", failed: "Failed", rejected: "Rejected", publishing: "Publishing", draft: "Draft",
    post: "Post", carousel: "Carousel", reel: "Reel", story: "Story",
    p_urun: "Product", p_surec: "Behind the scenes", p_ipucu: "Tips", p_topluluk: "Question / poll", p_kampanya: "Offer", p_kanit: "Review",
    planWeek: "Plan the week", newPost: "New post", approveAll: "Approve ready ones", reject: "Reject", edit: "Edit", ok: "Approve",
    save: "Save", cancel: "Cancel", del: "Delete", rewrite: "Rewrite", publishNow: "Publish now", duplicate: "Duplicate", close: "Close",
    caption: "Caption", hashtags: "Hashtags", alt: "Alt text", firstComment: "First comment", when: "Publish time",
    sponsored: "Paid partnership / ad", aiLabel: "Contains AI-generated visuals", why: "Why this?", checks: "Checks",
    noPending: "Nothing to review", noPendingT: "Plan the week; Tellal drafts posts from your library and brings them here.",
    swipeHint: "Swipe right: approve · left: reject · tap: edit",
    upload: "Add photos / videos", uploadHint: "Your own product photos and short vertical videos. Captions are written from these and your notes.",
    title: "Title (product name)", notes: "Notes", notesHint: "1–3 short sentences: material, features, size… Captions are built from this. Nothing is invented.", tags: "Tags",
    crop: "Crop", original: "Original", suggested: "suggested",
    reach: "Reach", interactions: "Interactions", saves: "Saves", shares: "Sends", follows: "Follows", views: "Views",
    loginT: "Sign in", password: "Password", login: "Sign in",
    sound: "Sounds", theme: "Theme", language: "Language", auto: "Auto", light: "Light", dark: "Dark",
    copied: "Copied", saved: "Saved", error: "Something went wrong",
    week: "Week", prev: "Previous", next: "Next", thisWeek: "This week",
  },
};
const store = {
  get(k, d) { try { const v = localStorage.getItem("tellal." + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem("tellal." + k, JSON.stringify(v)); } catch { /* private mode */ } },
};
let LANG = store.get("lang", (navigator.language || "tr").toLowerCase().startsWith("tr") ? "tr" : "en");
const t = (k) => DICT[LANG][k] ?? DICT.tr[k] ?? k;
const L = (tr, en) => (LANG === "tr" ? tr : en);

// ------------------------------------------------------------------ sounds
const AK = window.AppKit;
const kit = AK ? AK.uiSounds(new AK.SoundKit({ storageKey: "tellal.sound", volume: 0.7, reverb: 0.14, session: "ambient" })) : null;
const VOL = { tap: 0.28, select: 0.3, success: 0.42, error: 0.42, notify: 0.4, upload: 0.35, start: 0.35, stop: 0.35 };
const snd = (n) => kit && kit.play(n, { vol: VOL[n] ?? 0.35 }, 60);
const buzz = (ms = 10) => { try { navigator.vibrate && navigator.vibrate(ms); } catch { /* no vibration */ } };

// ------------------------------------------------------------------ helpers
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const nf = (n, d = 0) => new Intl.NumberFormat(LANG === "tr" ? "tr-TR" : "en-GB", { maximumFractionDigits: d, minimumFractionDigits: d }).format(n || 0);
const pct = (x, d = 1) => (LANG === "tr" ? "%" + nf(x * 100, d) : nf(x * 100, d) + "%");
const money = (n) => (LANG === "tr" ? nf(n) + " TL" : "TRY " + nf(n));
let S = { state: null, tz: "Europe/Istanbul" };

const ICON = {
  home: '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  stack: '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="m8 12 3 3 5-6"/>',
  cal: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
  img: '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/>',
  menu: '<circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  bolt: '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
  chat: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 21l1.9-5.3A8 8 0 1 1 21 12z"/>',
  tag: '<path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><circle cx="8" cy="8" r="1.6"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  edit: '<path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  play: '<path d="M7 4v16l13-8z"/>',
  layers: '<path d="m12 2 10 5-10 5L2 7z"/><path d="m2 17 10 5 10-5M2 12l10 5 10-5"/>',
  circle: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/>',
  heart: '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21.2l8.8-8.8a5.5 5.5 0 0 0 0-7.8z"/>',
  send: '<path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/>',
  bookmark: '<path d="m19 21-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
  warn: '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
  err: '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6M9 9l6 6"/>',
  left: '<path d="m15 18-6-6 6-6"/>', right: '<path d="m9 18 6-6-6-6"/>',
  copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  sound: '<path d="M4 9v6h4l5 4V5L8 9Z"/><path d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12"/>',
  mute: '<path d="M4 9v6h4l5 4V5L8 9Z"/><path d="M16 9l6 6M22 9l-6 6"/>',
  sparkle: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-2.6-6.4L21 8"/><path d="M21 3v5h-5"/>',
  wand: '<path d="m15 4 5 5L9 20H4v-5z"/><path d="m13 6 5 5"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
  bell: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.9 1.9 0 0 0 3.4 0"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  cards: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 7h6"/>',
  columns: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16M15 4v16"/>',
  download: '<path d="M12 3v12M7 10l5 5 5-5M5 21h14"/>',
  keyboard: '<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/>',
  trash: '<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/>',
};
const ic = (n, cls = "") => `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[n] || ""}</svg>`;
const FMT_ICON = { post: "img", carousel: "layers", reel: "play", story: "circle" };

function toast(msg, kind = "", action) {
  const el = document.createElement("div");
  el.className = "toast " + kind;
  const span = document.createElement("span"); span.textContent = msg; el.append(span);
  if (action) {
    const b = document.createElement("button"); b.textContent = action.label;
    b.onclick = () => { el.remove(); action.run(); };
    el.append(b);
  }
  $("#toasts").append(el);
  setTimeout(() => el.remove(), action ? 6000 : kind === "err" ? 5200 : 3000);
}

// Dates in the business's time zone, not the device's.
function dt(ts, opts) { return new Intl.DateTimeFormat(LANG === "tr" ? "tr-TR" : "en-GB", { timeZone: S.tz, ...opts }).format(new Date(ts * 1000)); }
const hm = (ts) => dt(ts, { hour: "2-digit", minute: "2-digit" });
const dayName = (ts) => dt(ts, { weekday: "long" });
const dayShort = (ts) => dt(ts, { weekday: "short", day: "numeric", month: "short" });
function zoneParts(ts) {
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-CA", { timeZone: S.tz, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23", weekday: "short" })
    .formatToParts(new Date(ts * 1000)).map((x) => [x.type, x.value]));
  return p;
}
function zoneOffset(ts) { const p = zoneParts(ts); const asUTC = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute); return Math.round((asUTC / 1000 - Math.floor(ts / 60) * 60) / 60); }
function toLocalInput(ts) { const p = zoneParts(ts); return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`; }
function fromLocalInput(v) { const [d, tm] = v.split("T"); const [y, m, dd] = d.split("-").map(Number); const [h, mi] = tm.split(":").map(Number); const guess = Date.UTC(y, m - 1, dd, h, mi) / 1000; return guess - zoneOffset(guess) * 60; }
function startOfDay(ts) { const p = zoneParts(ts); const guess = Date.UTC(+p.year, +p.month - 1, +p.day) / 1000; return guess - zoneOffset(guess) * 60; }
function relDay(ts) {
  const d0 = startOfDay(Date.now() / 1000), d = startOfDay(ts), diff = Math.round((d - d0) / 86400);
  if (diff === 0) return L("Bugün", "Today");
  if (diff === 1) return L("Yarın", "Tomorrow");
  if (diff === -1) return L("Dün", "Yesterday");
  return dayShort(ts);
}

// ------------------------------------------------------------------ API
async function api(path, opts = {}) {
  const sep = path.includes("?") ? "&" : "?";
  const init = { method: opts.method || (opts.body ? "POST" : "GET"), headers: {} };
  if (opts.body instanceof FormData) init.body = opts.body;
  else if (opts.body !== undefined) { init.body = JSON.stringify(opts.body); init.headers["content-type"] = "application/json"; }
  const r = await fetch(path + sep + "lang=" + LANG, init);
  if (r.status === 401 && !path.startsWith("api/login")) { showLogin(); throw new Error("login"); }
  const ct = r.headers.get("content-type") || "";
  const data = ct.includes("json") ? await r.json() : null;
  if (!r.ok) {
    const d = data && data.detail;
    const msg = typeof d === "string" ? d : (d && d.message) || t("error");
    const e = new Error(msg); e.status = r.status; e.data = d; throw e;
  }
  return data;
}
const fail = (e) => { if (e.message !== "login") { toast(e.message || t("error"), "err"); snd("error"); } };

// Media are fetched as blobs (so they also work in the in-browser build) and cached as object URLs.
const blobCache = new Map();
function mediaSrc(id) {
  if (!blobCache.has(id)) blobCache.set(id, fetch("media/" + id).then((r) => (r.ok ? r.blob() : null)).then((b) => (b ? URL.createObjectURL(b) : "")).catch(() => ""));
  return blobCache.get(id);
}
const posterCache = new Map();
function posterSrc(id) {
  if (!posterCache.has(id)) posterCache.set(id, fetch(`media/${id}/poster`).then((r) => (r.ok ? r.blob() : null)).then((b) => (b ? URL.createObjectURL(b) : "")).catch(() => ""));
  return posterCache.get(id);
}
let MEDIA = new Map();
async function loadMedia(force = false) {
  if (!force && MEDIA.size) return MEDIA;
  const list = await api("api/media");
  MEDIA = new Map(list.map((m) => [m.id, m]));
  return MEDIA;
}
// Fills elements marked data-media="id" once they come into view.
const io = "IntersectionObserver" in window ? new IntersectionObserver((ents) => ents.forEach((e) => { if (e.isIntersecting) { io.unobserve(e.target); paintMedia(e.target); } }), { rootMargin: "300px" }) : null;
async function paintMedia(el) {
  const id = +el.dataset.media;
  const m = MEDIA.get(id);
  if (m && m.kind === "video" && el.tagName !== "VIDEO") {
    // Thumbnails of videos use the poster frame saved on upload, so the whole video isn't downloaded.
    const poster = await posterSrc(id);
    if (poster) el.style.backgroundImage = `url("${poster}")`;
    else if (!el.querySelector(".vthumb")) el.insertAdjacentHTML("afterbegin", `<span class="vthumb">${ic("play")}</span>`);
    return;
  }
  const url = await mediaSrc(id);
  if (!url) return;
  if (el.tagName === "VIDEO") { posterSrc(id).then((p) => { if (p) el.poster = p; }); el.src = url; return; }
  el.style.backgroundImage = `url("${url}")`;
}
// Numbers count up once when they appear.
function countUp(root) {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  $$("[data-count]", root).forEach((el) => {
    const end = +el.dataset.count; if (!end || el.dataset.done) return;
    el.dataset.done = 1;
    const t0 = performance.now(), dur = 900 + Math.min(600, String(end).length * 90);
    const tick = (now) => { const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 4); el.textContent = nf(Math.round(end * e)); if (k < 1) requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  });
}
function hydrate(root = document) {
  countUp(root);
  $$("[data-media]", root).forEach((el) => (io ? io.observe(el) : paintMedia(el)));
  $$("textarea.input", root).forEach(grow);
}
// Text areas grow with their content (up to a limit), so nothing hides behind a scrollbar.
function grow(ta) { ta.style.height = "auto"; ta.style.height = Math.min(ta.scrollHeight + 2, 420) + "px"; }
document.addEventListener("input", (e) => { if (e.target.matches && e.target.matches("textarea.input")) grow(e.target); });
const thumb = (id, fmt, cls = "thumb") => `<span class="${cls}" data-media="${id}">${fmt ? `<span class="fmt">${ic(FMT_ICON[fmt])}</span>` : ""}</span>`;

// ------------------------------------------------------------------ shell, router
const ROUTES = [
  { id: "", key: "today", icon: "home", tab: true, render: viewToday },
  { id: "onay", key: "approve", icon: "stack", tab: true, badge: () => S.state?.counts.pending, render: viewApprove },
  { id: "takvim", key: "calendar", icon: "cal", tab: true, render: viewCalendar },
  { id: "kutuphane", key: "library", icon: "img", tab: true, render: viewLibrary },
  { id: "analiz", key: "analysis", icon: "chart", render: viewAnalysis },
  { id: "reklam", key: "ads", icon: "bolt", render: viewAds },
  { id: "yorumlar", key: "comments", icon: "chat", badge: () => S.state?.counts.comments, render: viewComments },
  { id: "marka", key: "brand", icon: "tag", render: viewBrand },
  { id: "ayarlar", key: "settings", icon: "gear", render: viewSettings },
];
function route() { const h = location.hash.replace(/^#\/?/, ""); const [id, q] = h.split("?"); return { id: id || "", q: new URLSearchParams(q || "") }; }
function go(id) { location.hash = "#/" + id; }

function paintNav() {
  const cur = route().id;
  const badge = (r) => { const n = r.badge && r.badge(); return n ? `<span class="badge">${n > 99 ? "99+" : n}</span>` : ""; };
  const moreActive = !ROUTES.find((r) => r.id === cur)?.tab;
  $("#tabs").innerHTML = ROUTES.filter((r) => r.tab).map((r) => `<a class="tab" href="#/${r.id}" ${r.id === cur ? 'aria-current="page"' : ""}>${ic(r.icon)}<span>${t(r.key)}</span>${badge(r)}</a>`).join("")
    + `<button class="tab" id="moreTab" ${moreActive ? 'aria-current="page"' : ""}>${ic("menu")}<span>${t("more")}</span>${(S.state?.counts.comments ? '<span class="badge">' + S.state.counts.comments + "</span>" : "")}</button>`;
  $("#moreTab").onclick = () => { snd("tap"); openMore(); };
  const link = (r) => `<a href="#/${r.id}" ${r.id === cur ? 'aria-current="page"' : ""}>${ic(r.icon)}<span>${t(r.key)}</span>${badge(r)}</a>`;
  const groups = [[L("Yayın", "Publishing"), ["", "onay", "takvim", "kutuphane"]], [L("Büyüme", "Growth"), ["analiz", "reklam", "yorumlar"]], [L("Hesap", "Account"), ["marka", "ayarlar"]]];
  const acc = S.state?.accounts?.[0];
  $("#side").innerHTML = `<div class="brand"><span class="logo"></span><span class="wordmark">tellal</span></div>`
    + groups.map(([g, ids]) => `<div class="group">${g}</div>` + ids.map((id) => link(ROUTES.find((r) => r.id === id))).join("")).join("")
    + `<div class="foot"><span class="av">${esc((S.state?.brand?.name || "T").trim().slice(0, 1).toLocaleUpperCase("tr"))}</span><span class="grow"><b class="ellipsis">${esc(S.state?.brand?.name || "")}</b>${acc ? "@" + esc(acc.username) + " · " : ""}${S.state?.mode === "demo" ? L("demo", "demo") : "Instagram"}</span></div>`;
  const acts = $("#topActions");
  const mac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
  acts.innerHTML = `<button class="searchbtn" id="cmdBtn">${ic("search")}<span>${L("Ara veya git…", "Search or jump to…")}</span><span class="kbd">${mac ? "⌘" : "Ctrl"} K</span></button>`
    + `<button class="icon-btn srch" id="cmdBtn2" aria-label="${L("Ara", "Search")}">${ic("search")}</button>`
    + (S.state?.mode === "demo" ? `<button class="demo-chip" id="demoChip"><i></i>Demo</button>` : "")
    + `<button class="btn sm primary newbtn" id="newBtn">${ic("plus")} ${t("newPost")}</button>`
    + `<button class="icon-btn" id="bellBtn" aria-label="${L("Bildirimler", "Notifications")}" title="${L("Bildirimler", "Notifications")}">${ic("bell")}${unread() ? '<span class="dotn"></span>' : ""}</button>`
    + `<button class="icon-btn" id="themeBtn" aria-label="${t("theme")}" title="${t("theme")}">${ic(isDark() ? "sun" : "moon")}</button>`
    + `<button class="icon-btn" id="sndBtn" title="${t("sound")}" aria-label="${t("sound")}">${ic(kit && kit.enabled ? "sound" : "mute")}</button>`;
  const dc = $("#demoChip");
  if (dc) dc.onclick = () => { snd("tap"); sheet(`<p style="margin-top:0">${L("Bu, uydurma bir işletmenin (Lale Deri Atölyesi) hesabı. Planlar, paylaşımlar, yorumlar ve sayılar simüle edilir; gerçek Instagram'a hiçbir şey gitmez.", "This is a made-up business (Lale Deri Atölyesi). Plans, posts, comments and numbers are simulated; nothing goes to real Instagram.")}</p>
    <p>${S.state.in_browser ? L("Uygulamanın tamamı şu an bu tarayıcıda çalışıyor; verileriniz cihazınızdan çıkmaz.", "The whole app is running in this browser; your data stays on this device.") : L("Gerçek hesap bağlamak için README'deki 'Instagram bağlantısı' adımlarına bakın.", "To connect a real account, see 'Connecting Instagram' in the README.")}</p>
    <p class="hint">${L("İstediğiniz gibi kurcalayın: onaylayın, silin, fotoğraf yükleyin. Ayarlar → Demoyu sıfırla ile baştan başlarsınız.", "Play freely: approve, delete, upload. Settings → Reset demo starts over.")}</p>`, { title: L("Demo modu", "Demo mode") }); };
  $("#sndBtn").onclick = () => { if (!kit) return; kit.setEnabled(!kit.enabled); snd("tap"); paintNav(); };
  $("#cmdBtn").onclick = $("#cmdBtn2").onclick = () => palette();
  $("#themeBtn").onclick = (e) => toggleTheme(e);
  $("#bellBtn").onclick = () => notifications();
  $("#newBtn").onclick = () => { pickMode = { ids: [] }; snd("tap"); if (route().id === "kutuphane") render(); else go("kutuphane"); };
}
const ROUTE_DESC = {
  analiz: ["Ne işe yaradı, ne zaman", "What worked, and when"], reklam: ["Öne çıkarılacaklar, bütçe", "What to boost, budget"],
  yorumlar: ["Yanıt taslakları", "Reply drafts"], marka: ["Ses, ürünler, ritim", "Voice, products, rhythm"], ayarlar: ["Hesap, görünüm, yedek", "Account, look, backup"],
};
function openMore() {
  const items = ROUTES.filter((r) => !r.tab);
  sheet(`<div class="moregrid">${items.map((r) => `<a href="#/${r.id}" data-close>${ic(r.icon)}<b>${t(r.key)}${r.badge && r.badge() ? ` <span class="pill pending">${r.badge()}</span>` : ""}</b><small>${L(...(ROUTE_DESC[r.id] || ["", ""]))}</small></a>`).join("")}</div>
    <div class="row" style="margin-top:12px"><button class="btn grow" data-close id="moreSearch">${ic("search")} ${L("Ara veya git…", "Search or jump to…")}</button><button class="btn sq" id="moreTheme" aria-label="${t("theme")}">${ic(isDark() ? "sun" : "moon")}</button><button class="btn sq" id="moreSnd" aria-label="${t("sound")}">${ic(kit && kit.enabled ? "sound" : "mute")}</button></div>`, { title: t("more") });
  $("#moreSearch").onclick = () => setTimeout(palette, 50);
  $("#moreTheme").onclick = (e) => { toggleTheme(e); setTimeout(() => { $("#moreTheme").innerHTML = ic(isDark() ? "sun" : "moon"); }, 50); };
  $("#moreSnd").onclick = () => { if (!kit) return; kit.setEnabled(!kit.enabled); snd("tap"); $("#moreSnd").innerHTML = ic(kit.enabled ? "sound" : "mute"); paintNav(); };
}

// ------------------------------------------------------------------ theme switch (circle reveal)
const isDark = () => document.documentElement.dataset.theme ? document.documentElement.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
function toggleTheme(e) {
  const next = isDark() ? "light" : "dark";
  const apply = () => { store.set("theme", next); applyTheme(); paintNav(); };
  snd("tap");
  if (!document.startViewTransition || matchMedia("(prefers-reduced-motion: reduce)").matches) { apply(); return; }
  const x = e ? e.clientX : innerWidth - 40, y = e ? e.clientY : 30;
  const r = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
  document.startViewTransition(apply).ready.then(() => {
    document.documentElement.animate({ clipPath: [`circle(0 at ${x}px ${y}px)`, `circle(${r}px at ${x}px ${y}px)`] },
      { duration: 550, easing: "cubic-bezier(.2,.8,.2,1)", pseudoElement: "::view-transition-new(root)" });
  }).catch(() => {});
}

// ------------------------------------------------------------------ notifications
const unread = () => (S.state?.events || []).filter((e) => e.ts > store.get("seen", 0)).length;
function notifications() {
  snd("tap");
  const seen = store.get("seen", 0);
  const evs = S.state?.events || [];
  const icon = (k) => ({ published: "send", approved: "check", failed: "warn", retry: "refresh", plan: "wand", reply: "chat", draft: "edit", rejected: "x", account: "link", brand: "tag", demo: "sparkle", bulk: "stack" }[k] || "bell");
  const wrap = document.createElement("div");
  wrap.className = "drawer-wrap";
  wrap.innerHTML = `<div class="drawer-bg"></div><aside class="drawer" role="dialog" aria-label="${L("Bildirimler", "Notifications")}"><header><h2>${L("Bildirimler", "Notifications")}</h2><button class="icon-btn" data-x aria-label="${t("close")}">${ic("x")}</button></header>
    <div class="body">${evs.length ? evs.map((e) => `<div class="nt ${e.post_id ? "link" : ""} ${e.ts > seen ? "new" : ""}" ${e.post_id ? `data-p="${e.post_id}"` : ""}><span class="ic">${ic(icon(e.kind))}</span><div class="grow"><p>${esc(e.message)}</p><small>${relDay(e.ts)} · ${hm(e.ts)}</small></div></div>`).join("") : `<div class="empty">${ic("bell")}<h3>${L("Sessiz", "All quiet")}</h3><p>${L("Paylaşımlar, onaylar ve hatalar burada görünür.", "Publishing, approvals and errors show up here.")}</p></div>`}</div></aside>`;
  document.body.append(wrap);
  const close = () => { wrap.remove(); paintNav(); };
  wrap.querySelector(".drawer-bg").onclick = close;
  wrap.querySelector("[data-x]").onclick = close;
  wrap.addEventListener("click", (e) => { const n = e.target.closest("[data-p]"); if (n) { close(); openEditor(+n.dataset.p); } });
  wrap.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
  if (evs.length) store.set("seen", Math.max(...evs.map((e) => e.ts)));
  wrap.querySelector("[data-x]").focus();
}

// ------------------------------------------------------------------ command palette (Ctrl/Cmd+K)
let PAL = null;
async function palette() {
  if (PAL) return;
  closeSheet();
  snd("tap");
  const wrap = document.createElement("div");
  wrap.className = "cmdk-wrap";
  wrap.innerHTML = `<div class="cmdk-bg"></div><div class="cmdk" role="dialog" aria-label="${L("Komutlar", "Commands")}"><div class="cmdk-in">${ic("search")}<input id="cmdIn" placeholder="${L("Sayfa, işlem, gönderi ya da medya ara…", "Search pages, actions, posts or media…")}" autocomplete="off" spellcheck="false"><span class="kbd">Esc</span></div><div class="cmdk-list" id="cmdList" role="listbox"></div>
    <div class="cmdk-foot"><span><span class="kbd">↑</span> <span class="kbd">↓</span> ${L("seç", "move")}</span><span><span class="kbd">↵</span> ${L("aç", "open")}</span><span><span class="kbd">Esc</span> ${L("kapat", "close")}</span></div></div>`;
  document.body.append(wrap);
  PAL = wrap;
  const input = $("#cmdIn", wrap), list = $("#cmdList", wrap);
  const close = () => { wrap.remove(); PAL = null; };
  wrap.querySelector(".cmdk-bg").onclick = close;
  const nav = ROUTES.map((r) => ({ g: L("Sayfalar", "Pages"), icon: r.icon, label: t(r.key), run: () => go(r.id) }));
  const actions = [
    { icon: "wand", label: t("planWeek"), run: () => planWeek() },
    { icon: "plus", label: L("Fotoğraf / video yükle", "Upload photos / videos"), run: () => { go("kutuphane"); setTimeout(() => $("#fileIn") && $("#fileIn").click(), 400); } },
    { icon: "sparkle", label: L("Seçerek yeni içerik üret", "Create a post from the library"), run: () => { pickMode = { ids: [] }; go("kutuphane"); } },
    { icon: "check", label: t("approveAll"), run: () => approveAll() },
    { icon: "copy", label: L("Biyografi önerilerini aç", "Open bio ideas"), run: () => go("marka") },
    { icon: "sound", label: kit && kit.enabled ? L("Sesleri kapat", "Turn sounds off") : L("Sesleri aç", "Turn sounds on"), run: () => { kit && kit.setEnabled(!kit.enabled); paintNav(); } },
    { icon: "circle", label: L("Temayı değiştir (açık / koyu)", "Toggle light / dark"), run: () => toggleTheme() },
    { icon: "link", label: LANG === "tr" ? "Switch to English" : "Türkçe'ye geç", run: () => { LANG = LANG === "tr" ? "en" : "tr"; store.set("lang", LANG); document.documentElement.lang = LANG; render(); } },
  ].map((a) => ({ ...a, g: L("İşlemler", "Actions") }));
  let posts = [];
  api("api/posts").then((ps) => { posts = ps; if (input.value) draw(); }).catch(() => {});
  let items = [], sel = 0;
  const norm = (x) => (x || "").toLocaleLowerCase("tr").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/ı/g, "i");
  const draw = () => {
    const q = norm(input.value.trim());
    const match = (x) => !q || norm(x).includes(q);
    items = [...nav.filter((x) => match(x.label)), ...actions.filter((x) => match(x.label))];
    if (q.length >= 2) {
      items.push(...posts.filter((p) => match(p.caption) || match(p.story_text)).slice(0, 6).map((p) => ({ g: L("İçerikler", "Posts"), media: p.media_ids[0], fmt: p.format,
        label: ((p.caption || p.story_text || "").split("\n")[0] || t(p.format)).slice(0, 70), hint: t(p.status), run: () => openEditor(p.id) })));
      items.push(...[...MEDIA.values()].filter((m) => !m.parent_id && (match(m.title) || match(m.notes))).slice(0, 5).map((m) => ({ g: L("Kütüphane", "Library"), media: m.id,
        label: m.title || L("Adsız", "Untitled"), hint: m.kind === "video" ? "Video" : L("Fotoğraf", "Photo"), run: () => { go("kutuphane"); setTimeout(() => mediaSheet(m.id), 450); } })));
    }
    sel = Math.min(sel, Math.max(0, items.length - 1));
    let g = "";
    list.innerHTML = items.length ? items.map((x, i) => { const head = x.g !== g ? `<div class="cmdk-group">${esc((g = x.g))}</div>` : ""; return head + `<button class="cmdk-item" role="option" data-i="${i}" aria-selected="${i === sel}">${x.media ? thumb(x.media, x.fmt, "thumb") : ic(x.icon)}<span class="ellipsis">${esc(x.label)}</span>${x.hint ? `<small>${esc(x.hint)}</small>` : ""}</button>`; }).join("")
      : `<div class="cmdk-empty">${L("Sonuç yok", "No results")}</div>`;
    hydrate(list);
    const cur = list.querySelector("[aria-selected=true]"); if (cur) cur.scrollIntoView({ block: "nearest" });
  };
  const run = (i) => { const x = items[i]; if (!x) return; close(); snd("select"); x.run(); };
  input.oninput = () => { sel = 0; draw(); };
  input.onkeydown = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(items.length - 1, sel + 1); draw(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(0, sel - 1); draw(); }
    else if (e.key === "Enter") { e.preventDefault(); run(sel); }
    else if (e.key === "Escape") { e.preventDefault(); close(); }
  };
  list.onclick = (e) => { const b = e.target.closest("[data-i]"); if (b) run(+b.dataset.i); };
  list.onmousemove = (e) => { const b = e.target.closest("[data-i]"); if (b && +b.dataset.i !== sel) { sel = +b.dataset.i; $$("[data-i]", list).forEach((x) => x.setAttribute("aria-selected", String(+x.dataset.i === sel))); } };
  draw();
  input.focus();
}
document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); PAL ? PAL.remove() || (PAL = null) : palette(); return; }
  if (e.key === "/" && !PAL && $("#sheet").hidden && !e.target.closest("input,textarea,select,[contenteditable]")) { e.preventDefault(); palette(); }
  if (e.key === "?" && !PAL && $("#sheet").hidden && !e.target.closest("input,textarea,select")) { e.preventDefault(); shortcutsSheet(); }
});
function shortcutsSheet() {
  const k = (x) => x.split(" ").map((y) => `<span class="kbd">${y}</span>`).join(" ");
  sheet(`<div class="shortcuts">
    ${k("Ctrl K")}<span>${L("Ara veya bir sayfaya git", "Search or jump anywhere")}</span>
    ${k("/")}<span>${L("Aramayı aç", "Open search")}</span>
    ${k("→")}<span>${L("Onay ekranında: onayla", "Review: approve")}</span>
    ${k("←")}<span>${L("Onay ekranında: reddet", "Review: reject")}</span>
    ${k("E")}<span>${L("Onay ekranında: düzenle", "Review: edit")}</span>
    ${k("Esc")}<span>${L("Pencereyi kapat", "Close the window")}</span>
    ${k("?")}<span>${L("Bu listeyi göster", "Show this list")}</span></div>`, { title: L("Klavye kısayolları", "Keyboard shortcuts") });
}

let renderSeq = 0;
async function render() {
  const { id, q } = route();
  const r = ROUTES.find((x) => x.id === id) || ROUTES[0];
  document.title = (r.id ? t(r.key) + " · " : "") + "Tellal";
  $("#title").textContent = t(r.key);
  paintNav();
  const seq = ++renderSeq;
  // A fresh element each time, so listeners a page added don't leak into the next page.
  const old = $("#view"), view = old.cloneNode(false);
  old.replaceWith(view);
  view.innerHTML = `<div class="loading" aria-busy="true"><div class="sk" style="height:40px;width:55%;margin:10px 0 18px"></div><div class="sk" style="height:96px"></div><div class="sk" style="height:220px;margin-top:14px"></div></div>`;
  try {
    const html = await r.render(q);
    if (seq !== renderSeq) return;
    if (typeof html === "string") view.innerHTML = html;
    hydrate(view);
    r.after && r.after();
  } catch (e) {
    if (seq !== renderSeq) return;
    view.innerHTML = `<div class="empty">${ic("warn")}<h3>${t("error")}</h3><p>${esc(e.message)}</p><button class="btn" onclick="location.reload()">${ic("refresh")} ${L("Yenile", "Reload")}</button></div>`;
  }
}
async function refreshState() {
  S.state = await api("api/state");
  S.tz = S.state.timezone || S.tz;
  paintNav();
  const b = $("#banner");
  if (S.state.mode !== "demo" && !S.state.accounts.length) {
    b.hidden = false;
    b.innerHTML = L(`Instagram hesabı bağlı değil. <a href="#/ayarlar">Ayarlar</a> bölümünden bağlayın.`, `No Instagram account connected. Connect one in <a href="#/ayarlar">Settings</a>.`);
  } else b.hidden = true;
}

// ------------------------------------------------------------------ sheet
let sheetClose = null, lastFocus = null;
function sheet(html, { title = "", wide = false, foot = "", onClose } = {}) {
  const wrap = $("#sheet"), box = wrap.querySelector(".sheet");
  box.className = "sheet" + (wide ? " wide" : "");
  box.innerHTML = `<div class="grab"></div><div class="sheet-head"><h2>${esc(title)}</h2><button class="icon-btn" data-close aria-label="${t("close")}">${ic("x")}</button></div><div class="sheet-body">${html}</div>${foot ? `<div class="sheet-foot">${foot}</div>` : ""}`;
  wrap.hidden = false;
  document.body.style.overflow = "hidden";
  sheetClose = onClose || null;
  hydrate(box);
  lastFocus = document.activeElement;
  setTimeout(() => { const f = box.querySelector(".sheet-body input:not([type=checkbox]):not([type=file]),.sheet-body textarea") ; (f && !matchMedia("(pointer:coarse)").matches ? f : box.querySelector("[data-close]")).focus({ preventScroll: true }); }, 60);
  // swipe down on the grab handle closes it
  let y0 = null;
  box.querySelector(".grab").addEventListener("pointerdown", (e) => { y0 = e.clientY; });
  window.addEventListener("pointerup", function up(e) { if (y0 !== null && e.clientY - y0 > 60) closeSheet(); y0 = null; window.removeEventListener("pointerup", up); });
  return box;
}
function closeSheet() {
  const wrap = $("#sheet");
  if (wrap.hidden) return;
  wrap.hidden = true;
  document.body.style.overflow = "";
  const f = sheetClose; sheetClose = null;
  f && f();
  if (lastFocus && document.contains(lastFocus)) lastFocus.focus({ preventScroll: true });
}
document.addEventListener("click", (e) => { if (e.target.closest("[data-close]")) closeSheet(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeSheet(); });

// ------------------------------------------------------------------ Instagram preview
function igPreview(p, { idx = 0 } = {}) {
  const ids = p.media_ids || [];
  const tall = p.format === "reel" || p.format === "story";
  const user = S.state?.accounts?.[0]?.username || S.state?.brand?.handle || "markaniz";
  const extra = p.extra || {};
  let overlay = "";
  const baked = MEDIA.get(ids[0])?.parent_id; // a story image Tellal already printed the text on
  if (p.format === "story" && !baked) {
    const f = (extra.story_frames && extra.story_frames[0]) || (p.story_text || "").split("\n")[0] || "";
    overlay = `<div class="storybar">${(extra.story_frames || [1]).map(() => "<i></i>").join("")}</div>` + (f ? `<div class="overlay"><span>${esc(f)}</span></div>` : "");
  }
  if (p.format === "reel" && p.reel_hook) overlay = `<div class="overlay"><span>${esc(p.reel_hook)}</span></div><div class="reelbar"><b>${esc(user)}</b> · ${esc((p.caption || "").split("\n")[0].slice(0, 60))}</div>`;
  const cur = ids[idx] ?? ids[0];
  const m = MEDIA.get(cur);
  const mediaEl = m && m.kind === "video"
    ? `<video data-media="${cur}" muted playsinline loop autoplay preload="metadata"></video>`
    : `<span data-media="${cur}" style="position:absolute;inset:0;background:center/cover no-repeat"></span>`;
  const dots = ids.length > 1 ? `<div class="dots">${ids.map((_, i) => `<i class="${i === idx ? "on" : ""}"></i>`).join("")}</div><div class="count">${idx + 1}/${ids.length}</div>
    ${idx > 0 ? `<button class="nav l" data-nav="-1">${ic("left")}</button>` : ""}${idx < ids.length - 1 ? `<button class="nav r" data-nav="1">${ic("right")}</button>` : ""}` : "";
  let cap = "";
  if (p.format !== "story") {
    const full = p.caption || "";
    const tags = (p.hashtags || []).map((x) => "#" + x).join(" ");
    const short = full.length > 125 ? full.slice(0, 125).replace(/\s+\S*$/, "") : full;
    cap = `<div class="ig-cap"><b>${esc(user)}</b> <span class="cap-text">${esc(short)}</span>${full.length > 125 ? `<button class="more" data-more>… ${L("devamı", "more")}</button><span class="cap-rest" hidden>${esc(full.slice(short.length))}</span>` : ""}${tags ? `\n<span class="tags">${esc(tags)}</span>` : ""}</div>`;
  }
  return `<div class="ig" data-post="${p.id}">
    <div class="ig-head"><span class="ig-av"><i></i></span><span class="grow ellipsis">${esc(user)}</span>${p.sponsored ? `<small>${L("Ücretli ortaklık", "Paid partnership")}</small>` : ""}</div>
    <div class="ig-media ${tall ? "tall" : ""}">${mediaEl}${overlay}${dots}</div>
    ${p.format === "story" ? "" : `<div class="ig-acts">${ic("heart")}${ic("chat")}${ic("send")}<span class="save">${ic("bookmark")}</span></div>`}
    ${cap}</div>`;
}
function bindPreview(root, p) {
  root.addEventListener("click", (e) => {
    const more = e.target.closest("[data-more]");
    if (more) { e.stopPropagation(); more.nextElementSibling.hidden = false; more.remove(); return; }
    const nav = e.target.closest("[data-nav]");
    if (nav) {
      e.stopPropagation();
      const holder = nav.closest(".ig");
      const i = Math.max(0, Math.min(p.media_ids.length - 1, (+holder.dataset.idx || 0) + +nav.dataset.nav));
      const tmp = document.createElement("div");
      tmp.innerHTML = igPreview(p, { idx: i });
      const fresh = tmp.firstElementChild; fresh.dataset.idx = i;
      holder.replaceWith(fresh); hydrate(fresh.parentElement); snd("tap");
    }
  });
}
const findingsHtml = (f) => !f || !f.length ? "" : `<div class="findings">${f.map((x) => `<div class="finding ${x.level}">${ic(x.level === "error" ? "err" : x.level === "warn" ? "warn" : "info")}<span>${esc(x.message)}</span></div>`).join("")}</div>`;
const statusPill = (s) => `<span class="pill ${s}">${t(s)}</span>`;

// ------------------------------------------------------------------ TODAY
// Line chart for daily reach: this period solid, the one before dashed. Plain SVG, no library.
function lineChart(sr, { h = 180, compact = false, w } = {}) {
  // Drawn at the real pixel width, so text and lines keep their size on any screen.
  const vw = ($("#view") && $("#view").clientWidth) || 640, wide = innerWidth >= 700;
  const n = sr.current.length, W = Math.max(260, Math.round(w || (compact && wide ? (vw - 22) / 2 - 40 : vw - 40))), H = h, pl = compact ? 4 : 38, pr = 6, pt = 10, pb = compact ? 4 : 22;
  const smooth0 = (a) => a.map((_, i) => { const w2 = a.slice(Math.max(0, i - 1), i + 2); return w2.reduce((s2, v) => s2 + v, 0) / w2.length; });
  const max = Math.max(1, ...smooth0(sr.current), ...smooth0(sr.previous));
  const nice = (() => { const e = 10 ** Math.floor(Math.log10(max)); const m = max / e; return (m <= 2 ? 2 : m <= 5 ? 5 : 10) * e; })();
  const x = (i) => pl + (W - pl - pr) * (n <= 1 ? 0 : i / (n - 1));
  const y = (v) => pt + (H - pt - pb) * (1 - v / nice);
  // a 3-day moving average keeps single big posts from turning the line into a comb
  const smooth = (a) => a.map((_, i) => { const w = a.slice(Math.max(0, i - 1), i + 2); return w.reduce((s, v) => s + v, 0) / w.length; });
  const cur = smooth(sr.current), prev = smooth(sr.previous);
  const path = (a) => a.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join("");
  const grid = compact ? "" : [0, 0.5, 1].map((f) => `<line x1="${pl}" x2="${W - pr}" y1="${y(nice * f)}" y2="${y(nice * f)}"/><text class="lbl" x="${pl - 8}" y="${y(nice * f) + 3.5}" text-anchor="end">${(() => { const v = nice * f; return v >= 1000 ? nf(v / 1000, v % 1000 ? 1 : 0) + (LANG === "tr" ? "b" : "k") : nf(v); })()}</text>`).join("");
  const step = Math.ceil(n / 5);
  const xl = compact ? "" : sr.labels.map((d, i) => (i % step === 0 || i === n - 1) && !(i !== n - 1 && n - 1 - i < step / 2) ? `<text class="lbl" x="${x(i)}" y="${H - 4}" text-anchor="${i === 0 ? "start" : i === n - 1 ? "end" : "middle"}">${new Date(d + "T12:00:00").toLocaleDateString(LANG === "tr" ? "tr-TR" : "en-GB", { day: "numeric", month: "short" })}</text>` : "").join("");
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="${L("Günlük erişim", "Daily reach")}">
    <defs><linearGradient id="chartFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9b5cf6" stop-opacity=".22"/><stop offset="1" stop-color="#9b5cf6" stop-opacity="0"/></linearGradient>
      <linearGradient id="chartLine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#5b5ff6"/><stop offset=".6" stop-color="#9b5cf6"/><stop offset="1" stop-color="#f0569b"/></linearGradient></defs>
    <g class="grid">${grid}</g>${xl}
    <path class="prev" d="${path(prev)}" vector-effect="non-scaling-stroke"/>
    <path class="area" d="${path(cur)}L${x(n - 1)} ${y(0)}L${x(0)} ${y(0)}Z"/>
    <path class="cur" d="${path(cur)}" pathLength="1"/>
    <circle class="dot" cx="${x(n - 1)}" cy="${y(cur[n - 1])}" r="3.5"/></svg>`;
}

async function viewToday() {
  const now = Date.now() / 1000, wk = mondayOf(now);
  const [, , an, weekPosts] = await Promise.all([refreshState(), loadMedia(), api("api/analytics?days=30").catch(() => null), api(`api/posts?start=${wk}&end=${wk + 7 * 86400 + 7200}`).catch(() => [])]);
  const st = S.state, c = st.counts;
  const hello = (() => { const h = +zoneParts(Date.now() / 1000).hour; return h < 12 ? L("Günaydın", "Good morning") : h < 18 ? L("İyi günler", "Good afternoon") : L("İyi akşamlar", "Good evening"); })();
  const name = (st.brand.name && st.brand.name !== "Markam") ? st.brand.name.split(" ")[0] : "";
  const line = c.pending
    ? L(`<b>${c.pending} içerik</b> onayınızı bekliyor. Onayladıklarınız zamanı gelince kendiliğinden paylaşılır.`, `<b>${c.pending} posts</b> are waiting for you. Approved posts go out on time by themselves.`)
    : c.approved ? L(`Her şey yolunda: ${c.approved} içerik sırada, size iş yok.`, `All set: ${c.approved} posts are queued.`) : L("Sırada içerik yok. Haftayı birlikte planlayalım.", "Nothing queued. Let's plan the week.");
  const hero = `<div class="greet"><div class="eyebrow">${esc(dt(Date.now() / 1000, { weekday: "long", day: "numeric", month: "long" }))}</div>
    <h2>${hello}${name ? `, <em>${esc(name)}</em>` : ""}.</h2><p>${line}</p>
    <div class="row wrap">${c.pending ? `<a class="btn glow" href="#/onay">${ic("stack")} ${L("Onaylamaya başla", "Start reviewing")}</a><button class="btn" id="planBtn">${ic("wand")} ${t("planWeek")}</button>`
      : `<button class="btn glow" id="planBtn">${ic("wand")} ${t("planWeek")}</button><a class="btn" href="#/kutuphane">${ic("plus")} ${t("newPost")}</a>`}</div></div>`;
  const stats = `<div class="kpis">
    <a class="kpi ${c.pending ? "hot" : ""}" href="#/onay"><b data-count="${c.pending}">${c.pending}</b><span>${t("pending")}</span></a>
    <a class="kpi" href="#/takvim"><b data-count="${c.approved}">${c.approved}</b><span>${L("Sırada", "Queued")}</span></a>
    <a class="kpi" href="#/yorumlar"><b data-count="${c.comments}">${c.comments}</b><span>${L("Yanıt bekleyen yorum", "Comments to answer")}</span></a>
    <a class="kpi" href="#/analiz"><b data-count="${c.published_7d}">${c.published_7d}</b><span>${L("Son 7 günde paylaşılan", "Published, last 7 days")}</span></a></div>`;
  const setup = st.mode !== "demo" && (!st.brand.name || st.brand.name === "Markam")
    ? `<div class="card" style="margin-top:16px"><div class="spread"><div><h3>${L("Önce sizi tanıyalım", "First, tell Tellal about you")}</h3><p class="hint" style="margin:4px 0 0">${L("Üç kısa adım: işletme, ses, iletişim. İçerikler buna göre yazılır.", "Three short steps: business, voice, contact. Posts are written from this.")}</p></div><button class="btn primary sm" id="setupBtn">${L("Başla", "Start")}</button></div></div>` : "";
  const failed = c.failed ? `<div class="card" style="margin-top:12px;border-color:var(--err)"><div class="row">${ic("warn")}<b class="grow">${L(`${c.failed} paylaşım başarısız oldu`, `${c.failed} posts failed`)}</b><a class="btn sm" href="#/takvim">${L("Gör", "View")}</a></div></div>` : "";
  const next = st.next.length ? st.next.map((p) => `<button class="item" data-open="${p.id}">${thumb(p.media_ids[0], p.format)}<span class="grow"><b>${relDay(p.scheduled_at)} ${hm(p.scheduled_at)}</b> · ${t(p.format)}<br><small class="clamp2">${esc((p.caption || p.story_text || "").split("\n")[0])}</small></span>${statusPill(p.status)}</button>`).join("")
    : `<div class="empty" style="padding:16px">${L("Sırada içerik yok.", "Nothing queued.")}</div>`;
  const occ = st.occasions.length ? `<div class="section"><h2>${L("Yaklaşan özel günler", "Upcoming occasions")}</h2></div><div class="card"><div class="list">${st.occasions.slice(0, 4).map((o) => `<div class="item"><span class="pill ${o.in_days <= 7 ? "pending" : ""}">${o.in_days === 0 ? L("bugün", "today") : L(`${o.in_days} gün`, `${o.in_days} days`)}</span><span class="grow"><b>${esc(o.name)}</b><br><small>${esc(new Date(o.date + "T12:00:00").toLocaleDateString(LANG === "tr" ? "tr-TR" : "en-GB", { day: "numeric", month: "long", weekday: "long" }))}</small></span></div>`).join("")}</div><p class="hint">${L("Planlayıcı, özel güne 3 gün kala hazırlanan içeriği o güne göre yazar. Kampanya detaylarını siz eklersiniz; Tellal indirim uydurmaz.", "The planner writes posts for occasions within 3 days. You add offer details; Tellal never invents discounts.")}</p></div>` : "";
  const ev = st.events.length ? `<div class="section"><h2>${L("Son hareketler", "Activity")}</h2></div><div class="card"><div class="list">${st.events.slice(0, 8).map((e) => `<div class="item" ${e.post_id ? `data-open="${e.post_id}"` : ""}><small class="time">${relDay(e.ts) === L("Bugün", "Today") ? hm(e.ts) : dayShort(e.ts)}</small><span class="grow">${esc(e.message)}</span></div>`).join("")}</div></div>` : "";
  const days = [...Array(7)].map((_, i) => startOfDay(wk + i * 86400 + 7200));
  const strip = `<div class="strip">${days.map((d) => {
    const ps = weekPosts.filter((p) => { const ts = p.scheduled_at || p.published_at; return ts >= d && ts < d + 86400 && p.status !== "rejected"; });
    return `<a href="#/takvim" class="${d === startOfDay(now) ? "today" : ""}"><small>${esc(dt(d, { weekday: "short" }))}</small><b>${esc(dt(d, { day: "numeric" }))}</b><span class="dots">${ps.slice(0, 4).map((p) => `<i class="${p.status === "pending" ? "p" : p.status === "published" ? "d" : ""}"></i>`).join("")}</span></a>`;
  }).join("")}</div><div class="legend" style="justify-content:center"><span><i style="width:7px;height:7px;border-radius:50%;background:var(--accent)"></i>${t("pending")}</span><span><i style="width:7px;height:7px;border-radius:50%;background:var(--teal)"></i>${t("approved")}</span><span><i style="width:7px;height:7px;border-radius:50%;background:var(--ok)"></i>${t("published")}</span></div>`;
  const chg = an && an.change && an.change.reach;
  const reach = an && an.series ? `<div class="card"><div class="spread"><div><div class="eyebrow">${L("Erişim · son 30 gün", "Reach · last 30 days")}</div><div class="bigstat" style="margin-top:6px"><b data-count="${an.totals.reach}">${nf(an.totals.reach)}</b>${chg != null ? `<span class="delta ${chg >= 0 ? "up" : "down"}">${chg >= 0 ? "▲" : "▼"} ${pct(Math.abs(chg), 0)}</span>` : ""}</div></div><a class="btn sm ghost" href="#/analiz">${t("analysis")} ${ic("right")}</a></div><div style="margin-top:12px">${lineChart(an.series, { h: 120, compact: true })}</div></div>` : "";
  const overview = `<div class="cols" style="margin-top:22px"><div class="card"><div class="spread" style="margin-bottom:10px"><div class="eyebrow">${L("Bu hafta", "This week")}</div><a class="btn sm ghost" href="#/takvim">${t("calendar")} ${ic("right")}</a></div>${strip}</div>${reach}</div>`;
  return `${hero}${setup}${stats}${failed}${overview}<div class="cols"><div><div class="section"><h2>${L("Sıradaki paylaşımlar", "Up next")}</h2><a class="btn sm ghost" href="#/takvim">${t("calendar")} ${ic("right")}</a></div><div class="card"><div class="list">${next}</div></div></div><div>${occ}${ev}</div></div>`;
}
document.addEventListener("click", (e) => {
  const o = e.target.closest("[data-open]");
  if (o && !e.target.closest(".sheet") && o.dataset.open) { snd("tap"); openEditor(+o.dataset.open); }
  if (e.target.closest("#planBtn")) planWeek();
  if (e.target.closest("#setupBtn")) setupWizard();
});

// First run: three small steps instead of the whole brand form.
async function setupWizard() {
  const r = await api("api/brand");
  const b = r.brand;
  let step = 0;
  const tones = [["samimi", L("Samimi", "Warm")], ["profesyonel", L("Profesyonel", "Professional")], ["eglenceli", L("Eğlenceli", "Playful")], ["zarif", L("Zarif", "Elegant")], ["sade", L("Sade", "Plain")]];
  const ctas = [["dm", "DM"], ["whatsapp", "WhatsApp"], ["link", L("Link", "Link")], ["visit", L("Mağaza", "Store")], ["call", L("Telefon", "Phone")]];
  const pages = [
    () => `<label class="f">${L("İşletmenizin adı", "Business name")}</label><input class="input" id="w_name" value="${esc(b.name === "Markam" ? "" : b.name)}" placeholder="${L("örn. Lale Deri Atölyesi", "e.g. Lale Leather")}">
      <label class="f">${L("Ne satıyorsunuz?", "What do you sell?")}</label><select class="input" id="w_sector">${Object.entries(r.sectors).map(([k, v]) => `<option value="${k}" ${k === b.sector ? "selected" : ""}>${esc(v)}</option>`).join("")}</select>
      <label class="f">${L("Şehir", "City")}</label><input class="input" id="w_city" value="${esc(b.city)}">`,
    () => `<label class="f">${L("Nasıl konuşursunuz?", "How do you sound?")}</label><div class="chips" id="w_tone">${tones.map(([k, n]) => `<button class="chip" data-v="${k}" aria-pressed="${b.tone === k}">${n}</button>`).join("")}</div>
      <label class="f">${L("Sizi farklı kılan bir şey", "One thing that sets you apart")}</label><input class="input" id="w_usp" value="${esc(b.usps[0] || "")}" placeholder="${L("örn. Her ürün elde dikilir", "e.g. Every piece is hand-stitched")}">
      <p class="hint">${L("Açıklamalarda bu cümle kullanılır; ne kadar somut, o kadar iyi.", "Used in captions; the more concrete, the better.")}</p>`,
    () => `<label class="f">${L("Müşteri size nereden ulaşsın?", "How should customers reach you?")}</label><div class="chips" id="w_cta">${ctas.map(([k, n]) => `<button class="chip" data-v="${k}" aria-pressed="${b.cta === k}">${n}</button>`).join("")}</div>
      <label class="f">WhatsApp / ${L("telefon", "phone")}</label><input class="input" id="w_phone" inputmode="tel" value="${esc(b.whatsapp || b.phone)}">
      <label class="f">${L("Instagram kullanıcı adı", "Instagram handle")}</label><input class="input" id="w_handle" value="${esc(b.handle)}" placeholder="kullaniciadi">`,
  ];
  const read = () => {
    const v = (id) => { const el = $("#" + id); return el ? el.value.trim() : undefined; };
    const on = (id) => { const el = $(`#${id} [aria-pressed=true]`); return el ? el.dataset.v : undefined; };
    if (step === 0) { b.name = v("w_name") || b.name; b.sector = v("w_sector"); b.city = v("w_city"); }
    if (step === 1) { b.tone = on("w_tone") || b.tone; const u = v("w_usp"); if (u) b.usps = [u, ...b.usps.filter((x) => x !== u)]; }
    if (step === 2) { b.cta = on("w_cta") || b.cta; const ph = v("w_phone"); if (b.cta === "call") b.phone = ph; else b.whatsapp = ph; b.handle = (v("w_handle") || "").replace(/^@/, ""); }
  };
  const draw = () => {
    const box = sheet(`<div class="steps">${pages.map((_, i) => `<i class="${i <= step ? "on" : ""}"></i>`).join("")}</div>${pages[step]()}`,
      { title: [L("İşletme", "Business"), L("Ses", "Voice"), L("İletişim", "Contact")][step], foot: `${step ? `<button class="btn" id="wBack">${L("Geri", "Back")}</button>` : ""}<button class="btn primary" id="wNext">${step < 2 ? L("Devam", "Next") : L("Bitir", "Finish")}</button>` });
    box.addEventListener("click", (e) => { const c = e.target.closest(".chips [data-v]"); if (c) { $$("[data-v]", c.parentElement).forEach((x) => x.setAttribute("aria-pressed", String(x === c))); snd("tap"); } });
    const back = $("#wBack", box); if (back) back.onclick = () => { read(); step--; draw(); };
    $("#wNext", box).onclick = async () => {
      read();
      if (step === 0 && (!b.name || b.name === "Markam")) { toast(L("İşletme adını yazın", "Enter the business name"), "err"); return; }
      if (step < 2) { step++; snd("tap"); draw(); return; }
      try { await api("api/brand", { method: "PUT", body: b }); snd("success"); closeSheet(); toast(L("Hazırız. Şimdi birkaç ürün fotoğrafı ekleyin.", "All set. Now add a few product photos."), "ok"); go("kutuphane"); }
      catch (er) { fail(er); }
    };
  };
  draw();
}

async function planWeek(start) {
  snd("start");
  try {
    const r = await api("api/plan", { body: { start: start || null } });
    if (!r.created.length) toast(L("Bu hafta için plan zaten dolu.", "This week is already planned."));
    else { toast(L(`${r.created.length} içerik hazırlandı. Onayınızı bekliyor.`, `${r.created.length} posts drafted for review.`), "ok"); snd("success"); }
    r.notes.forEach((n) => toast(n));
    await refreshState();
    if (r.created.length && route().id !== "onay") go("onay"); else render();
  } catch (e) { fail(e); }
}

// ------------------------------------------------------------------ APPROVAL (swipe deck)
let DECK = [];
async function viewApprove() {
  await loadMedia();
  DECK = await api("api/posts?status=pending");
  DECK.sort((a, b) => (a.scheduled_at || 9e12) - (b.scheduled_at || 9e12));
  if (!DECK.length) return `<div class="empty">${ic("check")}<h3>${t("noPending")}</h3><p>${t("noPendingT")}</p><button class="btn primary" id="planBtn">${ic("wand")} ${t("planWeek")}</button></div>`;
  DECK_TOTAL = DECK.length;
  const toggle = `<div class="toolbar"><div class="left"><span class="muted">${L(`${DECK.length} içerik onay bekliyor`, `${DECK.length} waiting for review`)}</span></div><div class="right"><div class="seg" id="revV"><button data-v="cards" aria-pressed="${reviewView === "cards"}">${ic("cards")} ${L("Kart", "Cards")}</button><button data-v="list" aria-pressed="${reviewView === "list"}">${ic("list")} ${L("Liste", "List")}</button></div></div></div>`;
  if (reviewView === "list") return toggle + reviewTable();
  return toggle + `<div id="deckBox"></div>`;
}
let reviewView = store.get("reviewView", "cards");
const picked = new Set();
function reviewTable() {
  return `<div class="card" style="padding:0;overflow:auto"><table class="tbl"><thead><tr><th style="width:36px"><input type="checkbox" class="cb" id="cbAll" aria-label="${L("Tümünü seç", "Select all")}"></th><th></th><th>${L("Zaman", "When")}</th><th>${L("İçerik", "Post")}</th><th>${L("Konu", "Topic")}</th><th>${t("checks")}</th></tr></thead><tbody>
    ${DECK.map((p) => `<tr data-row="${p.id}" class="${picked.has(p.id) ? "sel" : ""}"><td><input type="checkbox" class="cb" data-pick="${p.id}" ${picked.has(p.id) ? "checked" : ""} aria-label="${L("Seç", "Select")}"></td><td>${thumb(p.media_ids[0], p.format)}</td>
      <td class="num" style="white-space:nowrap">${p.scheduled_at ? `${esc(relDay(p.scheduled_at))}<br><small>${hm(p.scheduled_at)}</small>` : "–"}</td>
      <td class="capcell"><div class="ellipsis">${esc(((p.caption || p.story_text || "").split("\n")[0]) || t(p.format))}</div><small>${t(p.format)}</small></td>
      <td><span class="tagpill">${t("p_" + (p.pillar || "urun"))}</span></td>
      <td>${p.blocked ? `<span class="issues">${L(`${p.counts.error} hata`, `${p.counts.error} errors`)}</span>` : p.counts.warn ? `<span class="issues w">${L(`${p.counts.warn} uyarı`, `${p.counts.warn} warnings`)}</span>` : `<span class="pill published">${L("Hazır", "Ready")}</span>`}</td></tr>`).join("")}
    </tbody></table></div><div id="bulk"></div>`;
}
function paintBulk() {
  const b = $("#bulk"); if (!b) return;
  b.innerHTML = picked.size ? `<div class="bulkbar"><b class="num">${picked.size}</b><span>${L("seçili", "selected")}</span><button class="btn sm" data-bulk="reject">${t("reject")}</button><button class="btn sm" data-bulk="delete">${ic("trash")}</button><button class="btn sm go" data-bulk="approve">${ic("check")} ${t("ok")}</button></div>` : "";
}
let DECK_TOTAL = 0;
document.addEventListener("keydown", (e) => {
  if (route().id !== "onay" || reviewView !== "cards" || PAL || !$("#sheet").hidden || e.target.closest("input,textarea,select") || !DECK.length) return;
  if (e.key === "ArrowRight") { e.preventDefault(); decide(DECK[0], true); }
  else if (e.key === "ArrowLeft") { e.preventDefault(); decide(DECK[0], false); }
  else if (e.key.toLowerCase() === "e" || e.key === "Enter") { e.preventDefault(); openEditor(DECK[0].id); }
});
ROUTES[1].after = () => {
  const rv = $("#revV");
  if (rv) rv.onclick = (e) => { const b = e.target.closest("[data-v]"); if (!b) return; reviewView = b.dataset.v; store.set("reviewView", reviewView); picked.clear(); snd("tap"); render(); };
  if (reviewView === "cards") { if (DECK.length) paintDeck(); return; }
  const v = $("#view");
  const sync = () => { $$("[data-pick]", v).forEach((c) => { c.checked = picked.has(+c.dataset.pick); c.closest("tr").classList.toggle("sel", c.checked); }); const all = $("#cbAll"); if (all) { all.checked = picked.size === DECK.length && DECK.length > 0; all.indeterminate = picked.size > 0 && picked.size < DECK.length; } paintBulk(); };
  v.onclick = async (e) => {
    const cb = e.target.closest("[data-pick]");
    if (cb) { const id = +cb.dataset.pick; cb.checked ? picked.add(id) : picked.delete(id); snd("tap"); sync(); return; }
    if (e.target.id === "cbAll") { if (e.target.checked) DECK.forEach((p) => picked.add(p.id)); else picked.clear(); snd("tap"); sync(); return; }
    const bb = e.target.closest("[data-bulk]");
    if (bb) {
      const action = bb.dataset.bulk;
      if (action === "delete" && !confirm(L(`${picked.size} içerik silinsin mi?`, `Delete ${picked.size} items?`))) return;
      try {
        const r = await api("api/posts/bulk", { body: { ids: [...picked], action } });
        toast(L(`${r.done} içerik işlendi` + (r.skipped ? `, ${r.skipped} atlandı (hatası olanlar onaylanmaz)` : ""), `${r.done} done` + (r.skipped ? `, ${r.skipped} skipped (posts with errors can't be approved)` : "")), r.skipped ? "" : "ok");
        snd(action === "approve" ? "success" : "select"); picked.clear(); await refreshState(); render();
      } catch (er) { fail(er); }
      return;
    }
    const row = e.target.closest("[data-row]");
    if (row) openEditor(+row.dataset.row);
  };
  sync();
};
async function approveAll() {
  try {
    const r = await api("api/posts/approve-all", { body: {} });
    toast(L(`${r.approved} onaylandı` + (r.skipped ? `, ${r.skipped} düzeltme bekliyor` : ""), `${r.approved} approved` + (r.skipped ? `, ${r.skipped} need fixes` : "")), "ok");
    snd("success"); await refreshState(); render();
  } catch (e) { fail(e); }
}
function paintDeck() {
  const box = $("#deckBox");
  if (!box) return;
  const p = DECK[0];
  if (!p) { refreshState().then(render); return; }
  const blocked = p.blocked;
  const done = DECK_TOTAL - DECK.length;
  box.innerHTML = `<div class="deck-top"><div class="progress"><i style="width:${Math.round(100 * done / Math.max(1, DECK_TOTAL))}%"></i></div><small class="num">${done + 1} / ${DECK_TOTAL}</small><button class="btn sm ghost" id="allBtn" title="${t("approveAll")}">${ic("check")} ${L("Hepsi", "All")}</button></div>
    <div class="deck"><div class="swipe enter" id="card"><span class="stamp yes">${L("Onay", "Yes")}</span><span class="stamp no">${L("Ret", "No")}</span>
      <div class="meta"><span class="tagpill">${t(p.format)}</span><span class="tagpill">${esc(p.scheduled_at ? relDay(p.scheduled_at) + " · " + hm(p.scheduled_at) : L("Zaman yok", "No time"))}</span><span class="tagpill">${t("p_" + (p.pillar || "urun"))}</span></div>
      ${igPreview(p)}</div>
    ${blocked ? `<div class="finding error" style="margin-top:10px">${ic("err")}<span>${L("Onaydan önce düzeltilmesi gereken bir şey var. Düzenle'ye dokunun.", "Something must be fixed before approval. Tap Edit.")}</span></div>` : p.counts.warn ? `<div class="finding warn" style="margin-top:10px">${ic("warn")}<span>${L(`${p.counts.warn} uyarı var, düzenleyip bakabilirsiniz.`, `${p.counts.warn} warnings; open to check.`)}</span></div>` : ""}
    <div class="deck-actions"><button class="round no" id="noBtn" aria-label="${t("reject")}">${ic("x")}</button><button class="round mid" id="editBtn" aria-label="${t("edit")}">${ic("edit")}</button><button class="round yes" id="yesBtn" aria-label="${t("ok")}">${ic("check")}</button></div>
    <div class="keys"><span><span class="kbd">←</span> ${t("reject")}</span><span><span class="kbd">E</span> ${t("edit")}</span><span><span class="kbd">→</span> ${t("ok")}</span></div>
    <details class="more why"><summary>${t("why")}</summary><ul>${(p.rationale || []).map((r) => `<li>${esc(r)}</li>`).join("")}</ul></details></div>`;
  hydrate(box);
  $("#allBtn").onclick = approveAll;
  const card = $("#card");
  bindPreview(card, p);
  const yes = card.querySelector(".stamp.yes"), no = card.querySelector(".stamp.no");
  let x0 = null, dx = 0, id = null, moved = false;
  card.addEventListener("pointerdown", (e) => { if (e.target.closest("button")) return; x0 = e.clientX; dx = 0; id = e.pointerId; moved = false; card.classList.add("drag"); });
  card.addEventListener("pointermove", (e) => {
    if (x0 === null || e.pointerId !== id) return;
    dx = e.clientX - x0;
    if (Math.abs(dx) > 8 && !moved) { moved = true; try { card.setPointerCapture(id); } catch { /* ok */ } }
    card.style.transform = `translateX(${dx}px) rotate(${dx / 22}deg)`;
    yes.style.opacity = Math.max(0, Math.min(1, dx / 110)); no.style.opacity = Math.max(0, Math.min(1, -dx / 110));
  });
  const end = () => {
    if (x0 === null) return;
    card.classList.remove("drag");
    const d = dx; x0 = null;
    if (!moved) { card.style.transform = ""; openEditor(p.id); return; }
    if (d > 110) decide(p, true);
    else if (d < -110) decide(p, false);
    else { card.style.transform = ""; yes.style.opacity = no.style.opacity = 0; }
  };
  card.addEventListener("pointerup", end);
  card.addEventListener("pointercancel", () => { x0 = null; card.classList.remove("drag"); card.style.transform = ""; });
  $("#yesBtn").onclick = () => decide(p, true);
  $("#noBtn").onclick = () => decide(p, false);
  $("#editBtn").onclick = () => { snd("tap"); openEditor(p.id); };
}
async function decide(p, ok) {
  const card = $("#card");
  try {
    await api(`api/posts/${p.id}/${ok ? "approve" : "reject"}`, { body: {} });
    buzz(ok ? 12 : 8);
    snd(ok ? "success" : "select");
    if (card) { card.style.transform = `translateX(${ok ? 520 : -520}px) rotate(${ok ? 18 : -18}deg)`; card.style.opacity = 0; }
    const gone = DECK.shift();
    S.state.counts.pending = Math.max(0, S.state.counts.pending - 1);
    paintNav();
    setTimeout(paintDeck, 220);
    toast(ok ? L("Onaylandı", "Approved") : L("Reddedildi", "Rejected"), ok ? "ok" : "", { label: L("Geri al", "Undo"), run: async () => {
      try { await api(`api/posts/${gone.id}/unapprove`, { body: {} }); DECK.unshift({ ...gone, status: "pending" }); DECK_TOTAL = Math.max(DECK_TOTAL, DECK.length); S.state.counts.pending++; paintNav(); if ($("#deckBox")) paintDeck(); else render(); snd("tap"); } catch (er) { fail(er); }
    } });
  } catch (e) {
    if (card) card.style.transform = "";
    fail(e);
    if (e.status === 422) openEditor(p.id);
  }
}

// ------------------------------------------------------------------ EDITOR
async function openEditor(id) {
  await loadMedia();
  let p;
  try { p = await api("api/posts/" + id); } catch (e) { return fail(e); }
  const editable = !["published", "publishing"].includes(p.status);
  const ex = p.extra || {};
  const pillars = ["urun", "surec", "ipucu", "topluluk", "kampanya", "kanit"];
  const left = `<div id="pv">${igPreview(p)}</div>
    ${p.format === "story" && editable && MEDIA.get(p.media_ids[0])?.kind === "image" ? `<button class="btn block" id="storyMake" style="margin-top:10px">${ic("wand")} ${L("Hikâye görselini hazırla (9:16, yazılı)", "Make the story image (9:16, with text)")}</button><p class="hint">${L("Instagram API hikâyeye yazı ya da çıkartma ekleyemez; Tellal yazıyı görselin üstüne basar.", "The API can't add text or stickers to Stories; Tellal prints the text onto the image.")}</p>` : ""}
    ${ex.reel_script && ex.reel_script.length ? `<div class="card" style="margin-top:12px"><h3>${L("Reels kurgusu", "Reel plan")}</h3><div class="script" style="margin-top:8px">${ex.reel_script.map((s) => `<b>${esc(s.t)}</b><span>${esc(s.shot)}<br><small>“${esc(s.text)}”</small></span>`).join("")}</div><p class="hint">${L("Videonuz hazırsa bu sadece bir öneri; yeni çekim yapacaksanız rehberiniz.", "If your video is ready this is just a suggestion; if you'll film, it's your shot list.")}</p></div>` : ""}
    ${ex.carousel_slides && ex.carousel_slides.length ? `<div class="card" style="margin-top:12px"><h3>${L("Kare metinleri", "Slide texts")}</h3><ol style="margin:8px 0 0;padding-left:20px">${ex.carousel_slides.map((s) => `<li>${esc(s)}</li>`).join("")}</ol></div>` : ""}
    ${p.rates ? `<div class="card" style="margin-top:12px"><h3>${L("Sonuçlar", "Results")}</h3><div class="grid g2" style="margin-top:8px"><div><b class="num">${nf(p.reach)}</b><br><small>${t("reach")}</small></div><div><b class="num">${nf(p.likes)}</b><br><small>${L("Beğeni", "Likes")}</small></div><div><b class="num">${nf(p.shares)}</b><br><small>${t("shares")} · ${pct(p.rates.send)}</small></div><div><b class="num">${nf(p.saves)}</b><br><small>${t("saves")} · ${pct(p.rates.save)}</small></div></div>${p.avg_watch_ms ? `<p class="hint">${L("Ortalama izlenme", "Average watch")}: ${nf(p.avg_watch_ms / 1000, 1)} sn</p>` : ""}${p.permalink ? `<a class="btn sm" href="${esc(p.permalink)}" target="_blank" rel="noopener">${ic("link")} Instagram</a>` : ""}</div>` : ""}`;
  const capLen = (p.caption || "").length;
  const right = editable ? `
    <div class="row wrap" style="gap:6px">${statusPill(p.status)}<span class="pill">${ex.engine === "llm" ? L("Yapay zekâ yazdı", "AI-written") : L("Şablon motoru", "Template engine")}</span>${p.error ? `<span class="pill failed" title="${esc(p.error)}">${esc(p.error.slice(0, 60))}</span>` : ""}</div>
    <label class="f">${L("Biçim", "Format")}</label><div class="seg" id="fmtSeg">${["post", "carousel", "reel", "story"].map((f) => `<button data-v="${f}" aria-pressed="${p.format === f}">${t(f)}</button>`).join("")}</div>
    <label class="f">${L("Konu", "Topic")}</label><div class="chips" id="pilSeg">${pillars.map((x) => `<button class="chip" data-v="${x}" aria-pressed="${p.pillar === x}">${t("p_" + x)}</button>`).join("")}</div>
    <div class="row wrap" style="margin-top:12px"><button class="btn sm" id="regen">${ic("refresh")} ${t("rewrite")}</button>${(S.state.brand.languages || []).length > 1 ? `<div class="seg" id="langSeg">${S.state.brand.languages.map((l) => `<button data-v="${l}" aria-pressed="${p.lang === l}">${l.toUpperCase()}</button>`).join("")}</div>` : ""}</div>
    ${p.format === "story"
      ? `<label class="f">${L("Hikâye kareleri (her satır bir kare)", "Story frames (one per line)")}</label><textarea class="input" id="story" rows="4">${esc(p.story_text || "")}</textarea>${ex.sticker ? `<p class="hint">${ic("info")} ${L("Paylaşımdan sonra uygulamadan ekleyin", "Add in the app after posting")}: ${esc(ex.sticker)}</p>` : ""}`
      : `<label class="f">${t("caption")}</label><textarea class="input" id="cap" rows="9">${esc(p.caption || "")}</textarea><div class="counter" id="capCount">${capLen} / 2200 · ${L("ilk 125 karakter görünür", "first 125 characters show")}</div>
         <label class="f">${t("hashtags")} <span id="tagCount" class="num"></span></label><div class="chips" id="tags"></div><input class="input" id="tagIn" placeholder="${L("etiket ekle, Enter", "add tag, Enter")}" style="margin-top:6px">
         ${(p.tag_ideas || []).length ? `<div class="chips" id="tagIdeas" style="margin-top:8px">${p.tag_ideas.map((x) => `<button class="chip suggest" data-tag="${esc(x)}">+ #${esc(x)}</button>`).join("")}</div>` : ""}
         <p class="hint">${L("Instagram Aralık 2025'ten beri gönderi başına en fazla 5 hashtag kabul ediyor (açıklama ve ilk yorum dahil).", "Instagram allows at most 5 hashtags per post since December 2025 (caption and first comment included).")}</p>
         ${p.format === "reel" ? `<label class="f">${L("Reels kancası (videonun üstündeki ilk yazı)", "Reel hook (first on-screen text)")}</label><input class="input" id="hook" value="${esc(p.reel_hook || "")}">` : ""}
         ${["post", "carousel"].includes(p.format) ? `<label class="f">${t("alt")}</label><input class="input" id="alt" value="${esc(p.alt_text || "")}">` : ""}
         <label class="f">${t("firstComment")}</label><input class="input" id="fc" value="${esc(p.first_comment || "")}" placeholder="${L("isteğe bağlı", "optional")}">`}
    <label class="f">${t("when")}</label><input class="input" type="datetime-local" id="when" value="${p.scheduled_at ? toLocalInput(p.scheduled_at) : ""}">
    <div class="chips" id="bestTimes" style="margin-top:8px"></div>
    <p class="hint">${L("Saat dilimi", "Time zone")}: ${esc(S.tz)}</p>
    <label class="switch"><span>${t("sponsored")}<br><small>${L("Ticari Reklam Yönetmeliği: açıklamanın başında #reklam / iş birliği ibaresi zorunlu.", "Must be disclosed at the start of the caption.")}</small></span><input type="checkbox" id="spon" ${p.sponsored ? "checked" : ""}></label>
    <label class="switch"><span>${t("aiLabel")}<br><small>${L("Instagram'da 'Yapay zekâ bilgisi' etiketi açılır.", "Sets Instagram's 'AI info' label.")}</small></span><input type="checkbox" id="ai" ${p.ai_label ? "checked" : ""}></label>
    <div style="margin-top:16px">${readyHtml(p)}</div>
    <h3 style="margin-top:14px">${t("checks")}</h3><div id="finds">${findingsHtml(p.findings) || `<div class="finding info">${ic("check")}<span>${L("Sorun yok.", "All good.")}</span></div>`}</div>
    <details class="more why"><summary>${t("why")}</summary><ul>${(p.rationale || []).map((r) => `<li>${esc(r)}</li>`).join("")}</ul></details>`
    : `<div class="row wrap" style="gap:6px">${statusPill(p.status)}${p.published_at ? `<span class="pill">${dayShort(p.published_at)} ${hm(p.published_at)}</span>` : ""}</div>
       <pre style="white-space:pre-wrap;font:inherit;margin-top:12px">${esc(p.caption || p.story_text || "")}</pre>
       ${(p.comments_list || []).length ? `<h3 style="margin-top:14px">${t("comments")}</h3>${p.comments_list.map((c) => `<p><b>@${esc(c.username)}</b> ${esc(c.text)}</p>`).join("")}` : ""}`;
  const foot = editable
    ? `<button class="btn danger sq" id="del" title="${t("del")}">${ic("x")}</button><button class="btn sq" id="dup" title="${t("duplicate")}">${ic("copy")}</button><button class="btn" id="saveBtn">${t("save")}</button>${p.status === "approved" ? `<button class="btn" id="unap">${L("Onayı geri al", "Unapprove")}</button>` : `<button class="btn primary" id="apBtn">${ic("check")} ${t("ok")}</button>`}<button class="btn" id="nowBtn">${ic("send")} ${t("publishNow")}</button>`
    : `<button class="btn" id="dup">${ic("copy")} ${L("Tekrar kullan", "Reuse")}</button>`;
  const box = sheet(`<div class="cols"><div>${left}</div><div>${right}</div></div>`, { title: `${t(p.format)} · ${p.scheduled_at ? relDay(p.scheduled_at) + " " + hm(p.scheduled_at) : t(p.status)}`, wide: true, foot, onClose: () => { if (route().id === "onay" || route().id === "takvim" || route().id === "") render(); } });
  bindPreview($("#pv", box), p);
  animateRings(box);

  // ---- wiring
  let tags = [...(p.hashtags || [])];
  const paintTags = () => {
    const tg = $("#tags", box); if (!tg) return;
    tg.innerHTML = tags.map((x, i) => `<span class="chip">#${esc(x)}<button class="x" data-i="${i}" aria-label="${t("del")}">${ic("x")}</button></span>`).join("");
    const capTags = ((($("#cap", box) || {}).value || "").match(/(^|\s)#[\p{L}\p{N}_]+/gu) || []).length;
    const n = tags.length + capTags;
    $("#tagCount", box).innerHTML = `<span class="${n > 5 ? "pill failed" : "pill"}">${n}/5</span>`;
  };
  const collect = () => {
    const b = {};
    const v = (s) => { const el = $(s, box); return el ? el.value : undefined; };
    if ($("#cap", box)) { b.caption = v("#cap"); b.hashtags = tags; b.first_comment = v("#fc"); }
    if ($("#alt", box)) b.alt_text = v("#alt");
    if ($("#hook", box)) b.reel_hook = v("#hook");
    if ($("#story", box)) b.story_text = v("#story");
    const w = v("#when"); b.scheduled_at = w ? fromLocalInput(w) : null;
    b.sponsored = $("#spon", box).checked; b.ai_label = $("#ai", box).checked;
    return b;
  };
  const reopen = (np) => { closeSheet(); openEditor(np.id); };
  const saveNow = async (quiet) => { const r = await api("api/posts/" + p.id, { method: "PATCH", body: collect() }); if (!quiet) { toast(t("saved")); snd("select"); } return r; };
  if (editable) {
    paintTags();
    const tg = $("#tags", box);
    if (tg) tg.onclick = (e) => { const b = e.target.closest("[data-i]"); if (b) { tags.splice(+b.dataset.i, 1); paintTags(); snd("tap"); } };
    const ti = $("#tagIdeas", box);
    if (ti) ti.onclick = (e) => { const b = e.target.closest("[data-tag]"); if (!b) return; if (!tags.includes(b.dataset.tag)) tags.push(b.dataset.tag); b.remove(); paintTags(); snd("tap"); };
    const bt = $("#bestTimes", box), when = $("#when", box);
    const paintBest = () => {
      if (!bt || !when) return;
      const ts = when.value ? fromLocalInput(when.value) : Date.now() / 1000 + 86400;
      const wd = { Mon: 0, Tue: 1, Wed: 2, Thu: 3, Fri: 4, Sat: 5, Sun: 6 }[zoneParts(ts).weekday];
      const hours = (S.state.best_slots || {})[wd] || [];
      if (p.format === "story") { bt.innerHTML = ""; return; }
      bt.innerHTML = hours.length ? `<small style="align-self:center">${L("Bu gün için en iyi saatler", "Best hours for this day")}:</small>` + hours.map((h) => `<button class="chip suggest" data-h="${h}">${String(h).padStart(2, "0")}:00</button>`).join("") : "";
    };
    if (bt) {
      paintBest();
      when.addEventListener("change", paintBest);
      bt.onclick = (e) => {
        const b = e.target.closest("[data-h]"); if (!b) return;
        const base = when.value || toLocalInput(Date.now() / 1000 + 86400);
        when.value = base.slice(0, 11) + String(b.dataset.h).padStart(2, "0") + ":00";
        snd("tap"); paintBest();
      };
    }
    const tin = $("#tagIn", box);
    if (tin) tin.onkeydown = (e) => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); const v = tin.value.replace(/[#\s,]/g, ""); if (v && !tags.includes(v)) { tags.push(v.toLocaleLowerCase("tr")); paintTags(); snd("tap"); } tin.value = ""; } };
    const cap = $("#cap", box);
    if (cap) cap.oninput = () => { const n = cap.value.length; const c = $("#capCount", box); c.textContent = `${n} / 2200 · ${L("ilk 125 karakter görünür", "first 125 characters show")}`; c.classList.toggle("over", n > 2200); paintTags(); };
    $("#fmtSeg", box).onclick = async (e) => { const b = e.target.closest("[data-v]"); if (!b || b.dataset.v === p.format) return; try { reopen(await api(`api/posts/${p.id}/regenerate`, { body: { format: b.dataset.v } })); snd("select"); } catch (er) { fail(er); } };
    $("#pilSeg", box).onclick = async (e) => { const b = e.target.closest("[data-v]"); if (!b) return; try { reopen(await api(`api/posts/${p.id}/regenerate`, { body: { pillar: b.dataset.v } })); snd("select"); } catch (er) { fail(er); } };
    const ls = $("#langSeg", box);
    if (ls) ls.onclick = async (e) => { const b = e.target.closest("[data-v]"); if (!b) return; try { reopen(await api(`api/posts/${p.id}/regenerate`, { body: { lang: b.dataset.v } })); snd("select"); } catch (er) { fail(er); } };
    $("#regen", box).onclick = async () => { try { reopen(await api(`api/posts/${p.id}/regenerate`, { body: {} })); snd("select"); } catch (er) { fail(er); } };
    $("#saveBtn", box).onclick = async () => { try { reopen(await saveNow()); } catch (er) { fail(er); } };
    const ap = $("#apBtn", box);
    if (ap) ap.onclick = async () => { try { await saveNow(true); await api(`api/posts/${p.id}/approve`, { body: {} }); toast(L("Onaylandı. Zamanı gelince paylaşılacak.", "Approved. It will go out on time."), "ok"); snd("success"); buzz(12); closeSheet(); refreshState(); } catch (er) { fail(er); if (er.data && er.data.findings) $("#finds", box).innerHTML = findingsHtml(er.data.findings); } };
    const un = $("#unap", box);
    if (un) un.onclick = async () => { try { reopen(await api(`api/posts/${p.id}/unapprove`, { body: {} })); } catch (er) { fail(er); } };
    $("#nowBtn", box).onclick = async () => {
      if (!confirm(L("Bu içerik şimdi paylaşılsın mı?", "Publish this now?"))) return;
      try { await saveNow(true); const r = await api(`api/posts/${p.id}/publish-now`, { body: {} }); toast(r.status === "published" ? L("Paylaşıldı!", "Published!") : L("Instagram işliyor, birazdan paylaşılacak.", "Instagram is processing; it will be live shortly."), "ok"); snd("success"); closeSheet(); refreshState(); }
      catch (er) { fail(er); if (er.data && er.data.findings) $("#finds", box).innerHTML = findingsHtml(er.data.findings); }
    };
    $("#del", box).onclick = async () => { if (!confirm(L("Bu içerik silinsin mi?", "Delete this?"))) return; try { await api("api/posts/" + p.id, { method: "DELETE" }); snd("stop"); closeSheet(); refreshState(); } catch (er) { fail(er); } };
    const sm = $("#storyMake", box);
    if (sm) sm.onclick = () => makeStoryImage(p).then(reopen).catch(fail);
  }
  const dup = $("#dup", box);
  if (dup) dup.onclick = async () => { try { const np = await api(`api/posts/${p.id}/duplicate`, { body: {} }); toast(L("Kopyalandı, onay listesine eklendi.", "Copied to the review list."), "ok"); reopen(np); } catch (er) { fail(er); } };
}

// Readiness: the handful of things that decide whether a post performs, as one score.
function readiness(p) {
  const cap = p.caption || "", first = cap.trim().split("\n")[0] || "", story = p.format === "story";
  const tags = (p.hashtags || []).length;
  const items = story ? [
    [L("Kareler yazılı", "Frames written"), (p.story_text || "").trim().split("\n").filter(Boolean).length >= 2],
    [L("Zamanı belli", "Scheduled"), !!p.scheduled_at],
    [L("Hata yok", "No errors"), !(p.counts && p.counts.error)],
  ] : [
    [L("Kanca ilk satırda", "Hook up front"), first.length >= 12 && first.length <= 125],
    [L("Gönder / kaydet daveti", "Send or save invite"), /gönder|ilet|kaydet|send|save|pošalj|sačuvaj|spremi|trimite|salva/i.test(cap)],
    [L("İletişim çağrısı", "Call to action"), /dm|whatsapp|link|biyografi|mağaza|ara|sipariş|order|bio|store|call|poruk|mesaj/i.test(cap)],
    [L("3–5 hashtag", "3–5 hashtags"), tags >= 3 && tags <= 5],
    ...(["post", "carousel"].includes(p.format) ? [[L("Alternatif metin", "Alt text"), !!(p.alt_text || "").trim()]] : []),
    ...(p.format === "reel" ? [[L("Reels kancası", "Reel hook"), !!(p.reel_hook || "").trim()]] : []),
    [L("Zamanı belli", "Scheduled"), !!p.scheduled_at],
    [L("Hata yok", "No errors"), !(p.counts && p.counts.error)],
  ];
  const ok = items.filter((x) => x[1]).length;
  return { score: Math.round((100 * ok) / items.length), items };
}
function readyHtml(p) {
  const { score, items } = readiness(p), C = 2 * Math.PI * 24;
  const word = score >= 90 ? L("Hazır", "Ready") : score >= 60 ? L("Neredeyse", "Almost") : L("Eksikler var", "Needs work");
  return `<div class="ready"><div class="ring"><svg viewBox="0 0 56 56"><defs><linearGradient id="rgrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5b5ff6"/><stop offset="1" stop-color="#f0569b"/></linearGradient></defs><circle class="bg" cx="28" cy="28" r="24"/><circle class="fg" cx="28" cy="28" r="24" stroke-dasharray="${C}" stroke-dashoffset="${C}" data-off="${C * (1 - score / 100)}"/></svg><b>${score}</b></div>
    <div class="grow"><h3>${L("Hazırlık", "Readiness")} · ${word}</h3><ul style="margin-top:6px">${items.map(([n, v]) => `<li class="${v ? "ok" : ""}">${esc(n)}</li>`).join("")}</ul></div></div>`;
}
function animateRings(root) { requestAnimationFrame(() => requestAnimationFrame(() => $$(".ring .fg", root).forEach((c) => (c.style.strokeDashoffset = c.dataset.off)))); }

// Story image: 1080x1920, blurred background, the photo, and the first frame's text on top.
async function makeStoryImage(p) {
  const id = p.media_ids[0];
  const url = await mediaSrc(id);
  const img = await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = url; });
  const W = 1080, H = 1920, c = document.createElement("canvas"); c.width = W; c.height = H;
  const g = c.getContext("2d");
  const cover = Math.max(W / img.width, H / img.height);
  g.filter = "blur(40px) brightness(.85)";
  g.drawImage(img, (W - img.width * cover) / 2, (H - img.height * cover) / 2, img.width * cover, img.height * cover);
  g.filter = "none";
  const fit = Math.min((W - 120) / img.width, (H * 0.62) / img.height);
  const w = img.width * fit, h = img.height * fit, x = (W - w) / 2, y = H * 0.28;
  g.save(); g.shadowColor = "rgba(0,0,0,.35)"; g.shadowBlur = 50; g.shadowOffsetY = 20;
  g.beginPath(); g.roundRect ? g.roundRect(x, y, w, h, 36) : g.rect(x, y, w, h); g.fillStyle = "#000"; g.fill(); g.restore();
  g.save(); g.beginPath(); g.roundRect ? g.roundRect(x, y, w, h, 36) : g.rect(x, y, w, h); g.clip(); g.drawImage(img, x, y, w, h); g.restore();
  const text = ((p.extra && p.extra.story_frames && p.extra.story_frames[0]) || (p.story_text || "").split("\n")[0] || "").trim();
  if (text) {
    g.font = "800 64px system-ui,-apple-system,Segoe UI,sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
    const words = text.split(/\s+/), lines = []; let line = "";
    for (const wd of words) { const tst = line ? line + " " + wd : wd; if (g.measureText(tst).width > W - 200 && line) { lines.push(line); line = wd; } else line = tst; }
    if (line) lines.push(line);
    const lh = 86, top = y - 60 - lines.length * lh;
    lines.slice(0, 4).forEach((ln, i) => {
      const tw = g.measureText(ln).width, cy = Math.max(170, top) + i * lh + lh / 2;
      g.fillStyle = "rgba(255,253,249,.95)"; g.beginPath(); g.roundRect ? g.roundRect(W / 2 - tw / 2 - 28, cy - 40, tw + 56, 80, 18) : g.rect(W / 2 - tw / 2 - 28, cy - 40, tw + 56, 80); g.fill();
      g.fillStyle = "#1d2321"; g.fillText(ln, W / 2, cy + 2);
    });
  }
  const handle = "@" + (S.state.accounts[0]?.username || S.state.brand.handle || "");
  g.font = "600 40px system-ui,sans-serif"; g.fillStyle = "rgba(255,255,255,.9)"; g.textAlign = "center"; g.fillText(handle, W / 2, H - 110);
  const blob = await new Promise((r) => c.toBlob(r, "image/jpeg", 0.88));
  const fd = new FormData();
  const m = MEDIA.get(id) || {};
  fd.append("file", blob, "story.jpg"); fd.append("title", (m.title || "") + L(" (hikâye)", " (story)")); fd.append("notes", m.notes || ""); fd.append("parent_id", String(id));
  const nm = await api("api/media", { body: fd });
  MEDIA.set(nm.id, nm);
  snd("upload");
  return api("api/posts/" + p.id, { method: "PATCH", body: { media_ids: [nm.id] } });
}

// ------------------------------------------------------------------ CALENDAR
let weekStart = null;
let calView = store.get("calView", matchMedia("(min-width: 900px)").matches ? "week" : "agenda");
let calFilter = "all";
const CAL_FILTERS = [["all", () => L("Tümü", "All")], ["pending", () => t("pending")], ["approved", () => t("approved")], ["published", () => t("published")], ["failed", () => t("failed")]];
async function viewCalendar() {
  await loadMedia();
  if (weekStart === null) weekStart = mondayOf(Date.now() / 1000);
  const end = weekStart + 7 * 86400 + 7200;
  const all = await api(`api/posts?start=${weekStart}&end=${end}`);
  const posts = all.filter((p) => (calFilter === "all" ? p.status !== "rejected" : p.status === calFilter));
  const today = startOfDay(Date.now() / 1000);
  const days = [...Array(7)].map((_, i) => startOfDay(weekStart + i * 86400 + 7200));
  const when = (p) => p.scheduled_at || p.published_at || p.created;
  const byDay = days.map((d) => posts.filter((p) => when(p) >= d && when(p) < d + 86400).sort((x, y) => when(x) - when(y)));
  const count = (st) => all.filter((p) => p.status === st).length;
  const head = `<div class="toolbar"><div class="left"><div class="row" style="gap:2px"><button class="icon-btn" id="wPrev" aria-label="${t("prev")}">${ic("left")}</button><button class="icon-btn" id="wNext" aria-label="${t("next")}">${ic("right")}</button></div>
      <b class="serif" style="font-size:22px">${dt(days[0], { day: "numeric", month: "short" })} – ${dt(days[6], { day: "numeric", month: "short", year: "numeric" })}</b>
      ${weekStart !== mondayOf(Date.now() / 1000) ? `<button class="btn sm" id="wNow">${t("thisWeek")}</button>` : ""}</div>
    <div class="right"><div class="seg" id="calV"><button data-v="week" aria-pressed="${calView === "week"}" title="${L("Hafta", "Week")}">${ic("columns")}</button><button data-v="agenda" aria-pressed="${calView === "agenda"}" title="${L("Liste", "Agenda")}">${ic("list")}</button></div>
      <button class="btn sm primary" id="wPlan">${ic("wand")} ${L("Haftayı doldur", "Fill the week")}</button></div></div>
    <div class="chips" id="calF" style="margin:-4px 0 16px">${CAL_FILTERS.map(([k, n]) => `<button class="chip" data-v="${k}" aria-pressed="${calFilter === k}">${n()}${k === "all" ? "" : ` <span class="muted num">${count(k)}</span>`}</button>`).join("")}</div>`;
  if (calView === "agenda") {
    const blocks = days.map((d, i) => byDay[i].length ? `<div class="agenda-day"><h3><b>${dt(d, { day: "numeric" })}</b><span>${esc(dt(d, { weekday: "long", month: "long" }))}</span>${d === today ? `<span class="today">${L("bugün", "today")}</span>` : ""}</h3><div class="card">${byDay[i].map((p) => `<button class="ag" data-open="${p.id}"><span class="time">${when(p) ? hm(when(p)) : "–"}</span>${thumb(p.media_ids[0], p.format)}<span class="cap"><span class="ellipsis" style="display:block">${esc(((p.caption || p.story_text || "").split("\n")[0]) || t(p.format))}</span><small>${t(p.format)} · ${t("p_" + (p.pillar || "urun"))}${p.blocked ? ` · <span class="issues">${L("düzeltme gerekli", "needs a fix")}</span>` : ""}</small></span>${statusPill(p.status)}</button>`).join("")}</div></div>` : "").join("");
    return head + (blocks || `<div class="empty">${ic("cal")}<h3>${L("Bu hafta boş", "Nothing this week")}</h3><p>${L("Planlayıcı, ritminize göre haftayı birkaç saniyede doldurur.", "The planner fills the week to your rhythm in seconds.")}</p></div>`);
  }
  const grid = `<div class="week">${days.map((d, i) => `<div class="day ${d === today ? "today" : ""} ${d < today ? "past" : ""}" data-day="${d}"><h3><b>${dt(d, { day: "numeric" })}</b><span>${dt(d, { weekday: "short" })}</span></h3>
    ${byDay[i].length ? byDay[i].map((p) => { const ts = when(p); const movable = ["pending", "approved", "failed"].includes(p.status); return `<button class="slot ${p.status} ${p.blocked ? "blocked" : ""}" data-open="${p.id}" ${movable ? `draggable="true" data-drag="${p.id}" data-ts="${ts}"` : ""}>${thumb(p.media_ids[0], p.format)}<span class="meta"><b>${ts ? hm(ts) : "–"}</b> ${t(p.format)}<br>${statusPill(p.status)}</span></button>`; }).join("") : `<small class="muted">—</small>`}</div>`).join("")}</div>
    <p class="hint">${L("İpucu: bekleyen ya da onaylı bir içeriği başka bir güne sürükleyin; saati aynı kalır.", "Tip: drag a pending or approved post to another day; the time stays the same.")}</p>`;
  return head + grid;
}
ROUTES[2].after = () => {
  $("#wPrev").onclick = () => { weekStart -= 7 * 86400; snd("tap"); render(); };
  $("#wNext").onclick = () => { weekStart += 7 * 86400; snd("tap"); render(); };
  const n = $("#wNow"); if (n) n.onclick = () => { weekStart = mondayOf(Date.now() / 1000); render(); };
  $("#calV").onclick = (e) => { const b = e.target.closest("[data-v]"); if (!b) return; calView = b.dataset.v; store.set("calView", calView); snd("tap"); render(); };
  $("#calF").onclick = (e) => { const b = e.target.closest("[data-v]"); if (!b) return; calFilter = b.dataset.v; snd("tap"); render(); };
  $("#wPlan").onclick = () => {
    const nowDay = startOfDay(Date.now() / 1000);
    const start = Math.max(weekStart, nowDay);
    const p = zoneParts(start + 7200);
    planWeek(`${p.year}-${p.month}-${p.day}`);
  };
  // drag a post to another day (keeps the hour)
  let dragId = null, dragTs = 0;
  $$("[data-drag]").forEach((el) => {
    el.addEventListener("dragstart", (e) => { dragId = +el.dataset.drag; dragTs = +el.dataset.ts; el.classList.add("dragging"); e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", String(dragId)); });
    el.addEventListener("dragend", () => { el.classList.remove("dragging"); $$(".day.drop-over").forEach((d) => d.classList.remove("drop-over")); });
  });
  $$(".day[data-day]").forEach((day) => {
    day.addEventListener("dragover", (e) => { if (dragId) { e.preventDefault(); day.classList.add("drop-over"); } });
    day.addEventListener("dragleave", () => day.classList.remove("drop-over"));
    day.addEventListener("drop", async (e) => {
      e.preventDefault(); day.classList.remove("drop-over");
      if (!dragId) return;
      const target = +day.dataset.day, from = startOfDay(dragTs);
      const p = zoneParts(dragTs), tp = zoneParts(target + 7200);
      const ts = fromLocalInput(`${tp.year}-${tp.month}-${tp.day}T${p.hour}:${p.minute}`);
      const id = dragId; dragId = null;
      if (target === from) return;
      if (ts < Date.now() / 1000) { toast(L("Geçmiş bir güne taşınamaz.", "Can't move into the past."), "err"); return; }
      try {
        const r = await api("api/posts/" + id, { method: "PATCH", body: { scheduled_at: ts } });
        snd("select");
        toast(r.status === "pending" ? L("Taşındı; değiştiği için yeniden onayınızı bekliyor.", "Moved; it needs your approval again.") : L("Taşındı.", "Moved."), "ok");
        refreshState(); render();
      } catch (er) { fail(er); }
    });
  });
};
function mondayOf(ts) { const p = zoneParts(ts); const wd = { Mon: 0, Tue: 1, Wed: 2, Thu: 3, Fri: 4, Sat: 5, Sun: 6 }[p.weekday]; return startOfDay(startOfDay(ts) - wd * 86400 + 7200); }

// ------------------------------------------------------------------ LIBRARY
let pickMode = null; // {ids:[]} when choosing media for a new post
let libFilter = "all", libSort = "new", libQuery = "";
async function viewLibrary() {
  await loadMedia(true);
  const list = [...MEDIA.values()].filter((m) => !m.parent_id);
  const n = { all: list.length, image: list.filter((m) => m.kind === "image").length, video: list.filter((m) => m.kind === "video").length, unused: list.filter((m) => !m.used).length };
  const head = `<div class="drop" id="drop">${ic("img")}<p>${t("uploadHint")}</p><label class="btn primary">${ic("plus")} ${t("upload")}<input type="file" id="fileIn" accept="image/*,video/mp4,video/quicktime" multiple hidden></label></div>
    <div class="toolbar" style="margin-top:16px"><div class="left"><div class="chips" id="libF">${[["all", L("Tümü", "All")], ["image", L("Fotoğraf", "Photos")], ["video", "Video"], ["unused", L("Hiç kullanılmamış", "Never used")]].map(([k, l]) => `<button class="chip" data-v="${k}" aria-pressed="${libFilter === k}">${l} <span class="muted num">${n[k]}</span></button>`).join("")}</div></div>
      <div class="right"><label class="search">${ic("search")}<input class="input" id="libQ" placeholder="${L("Başlık ya da not ara", "Search titles and notes")}" value="${esc(libQuery)}"></label>
      <select class="input" id="libS" style="height:34px;min-height:34px;width:auto;font-size:13.5px;padding:0 10px"><option value="new" ${libSort === "new" ? "selected" : ""}>${L("En yeni", "Newest")}</option><option value="least" ${libSort === "least" ? "selected" : ""}>${L("En az kullanılan", "Least used")}</option><option value="most" ${libSort === "most" ? "selected" : ""}>${L("En çok kullanılan", "Most used")}</option></select>
      <button class="btn sm ${pickMode ? "primary" : ""}" id="pickBtn"></button>${pickMode ? `<button class="btn sm ghost" id="pickCancel">${t("cancel")}</button>` : ""}</div></div>`;
  if (!list.length) return head + `<div class="empty">${ic("img")}<h3>${L("Kütüphane boş", "Library is empty")}</h3><p>${L("Ürün fotoğraflarınızı ekleyin. Tellal bunlardan içerik planlar; fotoğraf üretmez, sizinkileri kullanır.", "Add your product photos. Tellal plans from them; it doesn't generate images, it uses yours.")}</p></div>`;
  return head + `<div class="lib" id="lib"></div><div class="empty" id="libEmpty" hidden><h3>${L("Eşleşen dosya yok", "No matching files")}</h3></div>`;
}
function paintLibrary() {
  const box = $("#lib"); if (!box) return;
  const norm = (x) => (x || "").toLocaleLowerCase("tr");
  let list = [...MEDIA.values()].filter((m) => !m.parent_id)
    .filter((m) => libFilter === "all" || (libFilter === "unused" ? !m.used : m.kind === libFilter))
    .filter((m) => !libQuery || norm(m.title + " " + m.notes + " " + (m.tags || []).join(" ")).includes(norm(libQuery)));
  list.sort((a, b) => libSort === "least" ? (a.used || 0) - (b.used || 0) : libSort === "most" ? (b.used || 0) - (a.used || 0) : (b.created || b.id) - (a.created || a.id));
  const sel = pickMode ? pickMode.ids : [];
  box.innerHTML = list.map((m) => { const i = sel.indexOf(m.id); return `<button class="tile ${i >= 0 ? "sel" : ""}" data-m="${m.id}" data-media="${m.id}" title="${esc(m.title || "")}">${m.used ? `<span class="used">${m.used}×</span>` : ""}${m.kind === "video" ? `<span class="fmt">${ic("play")}</span>` : ""}${i >= 0 ? `<span class="check">${i + 1}</span>` : ""}<span class="t ellipsis">${esc(m.title || "")}</span></button>`; }).join("");
  $("#libEmpty").hidden = !!list.length;
  hydrate(box);
  const pb = $("#pickBtn");
  pb.innerHTML = pickMode ? `${ic("sparkle")} ${pickMode.ids.length ? L(`${pickMode.ids.length} seçili · içerik üret`, `${pickMode.ids.length} selected · create`) : L("Fotoğraf seçin", "Pick photos")}` : `${ic("check")} ${L("Seç ve içerik üret", "Select & create")}`;
  pb.disabled = !!pickMode && !pickMode.ids.length;
}
ROUTES[3].after = () => {
  $("#fileIn").onchange = (e) => { const f = [...e.target.files]; e.target.value = ""; if (f.length) uploadFlow(f); };
  const drop = $("#drop");
  drop.ondragover = (e) => { e.preventDefault(); drop.classList.add("over"); };
  drop.ondragleave = () => drop.classList.remove("over");
  drop.ondrop = (e) => { e.preventDefault(); drop.classList.remove("over"); uploadFlow([...e.dataTransfer.files]); };
  if (!$("#lib")) return;
  paintLibrary();
  $("#libF").onclick = (e) => { const b = e.target.closest("[data-v]"); if (!b) return; libFilter = b.dataset.v; $$("[data-v]", $("#libF")).forEach((x) => x.setAttribute("aria-pressed", String(x === b))); snd("tap"); paintLibrary(); };
  $("#libQ").oninput = (e) => { libQuery = e.target.value; paintLibrary(); };
  $("#libS").onchange = (e) => { libSort = e.target.value; paintLibrary(); };
  $("#pickBtn").onclick = () => { if (!pickMode) { pickMode = { ids: [] }; snd("tap"); render(); return; } if (pickMode.ids.length) newPostSheet(pickMode.ids); };
  const pc = $("#pickCancel"); if (pc) pc.onclick = () => { pickMode = null; render(); };
  $("#lib").onclick = (e) => {
    const el = e.target.closest(".tile"); if (!el) return;
    const id = +el.dataset.m;
    if (pickMode) { const i = pickMode.ids.indexOf(id); i >= 0 ? pickMode.ids.splice(i, 1) : pickMode.ids.length < 10 && pickMode.ids.push(id); snd("tap"); paintLibrary(); return; }
    mediaSheet(id);
  };
};
function newPostSheet(ids) {
  const vids = ids.filter((i) => MEDIA.get(i)?.kind === "video").length;
  const fmts = ids.length > 1 ? ["carousel"] : vids ? ["reel", "story"] : ["post", "story"];
  let fmt = fmts[0], pil = "urun", sponsored = false;
  const box = sheet(`<div class="row wrap" style="gap:6px">${ids.map((i) => thumb(i, MEDIA.get(i)?.kind === "video" ? "reel" : null)).join("")}</div>
    <label class="f">${L("Biçim", "Format")}</label><div class="seg" id="nf">${fmts.map((f) => `<button data-v="${f}" aria-pressed="${f === fmt}">${t(f)}</button>`).join("")}</div>
    <label class="f">${L("Konu", "Topic")}</label><div class="chips" id="np">${["urun", "surec", "ipucu", "topluluk", "kampanya", "kanit"].map((x) => `<button class="chip" data-v="${x}" aria-pressed="${x === pil}">${t("p_" + x)}</button>`).join("")}</div>
    <label class="f">${t("when")}</label><input class="input" type="datetime-local" id="nw" value="${toLocalInput(Date.now() / 1000 + 86400)}">
    <label class="switch"><span>${t("sponsored")}</span><input type="checkbox" id="ns"></label>`,
  { title: t("newPost"), foot: `<button class="btn" data-close>${t("cancel")}</button><button class="btn primary" id="nGo">${ic("sparkle")} ${L("Taslağı yaz", "Write draft")}</button>` });
  const seg = (sel, set) => { $(sel, box).onclick = (e) => { const b = e.target.closest("[data-v]"); if (!b) return; set(b.dataset.v); $$("[data-v]", $(sel, box)).forEach((x) => x.setAttribute("aria-pressed", String(x === b))); snd("tap"); }; };
  seg("#nf", (v) => (fmt = v)); seg("#np", (v) => (pil = v));
  $("#nGo", box).onclick = async () => {
    sponsored = $("#ns", box).checked;
    try {
      const w = $("#nw", box).value;
      const p = await api("api/posts", { body: { media_ids: ids, format: fmt, pillar: pil, sponsored, scheduled_at: w ? fromLocalInput(w) : null } });
      pickMode = null; snd("success"); closeSheet(); openEditor(p.id); refreshState();
    } catch (e) { fail(e); }
  };
}
function mediaSheet(id) {
  const m = MEDIA.get(id);
  const ratio = m.width && m.height ? (m.width / m.height).toFixed(2) : "?";
  const box = sheet(`<div class="ig-media ${m.kind === "video" || m.width / m.height < 0.7 ? "tall" : ""}" style="border-radius:14px;max-width:360px;margin:0 auto">${m.kind === "video" ? `<video data-media="${id}" controls playsinline></video>` : `<span data-media="${id}" style="position:absolute;inset:0;background:center/contain no-repeat"></span>`}</div>
    <p class="hint" style="text-align:center">${m.width}×${m.height} · ${ratio}${m.duration ? ` · ${nf(m.duration, 1)} sn` : ""} · ${nf((m.size || 0) / 1024)} KB · ${L("kullanım", "used")}: ${m.used || 0}</p>
    <label class="f">${t("title")}</label><input class="input" id="mt" value="${esc(m.title || "")}">
    <label class="f">${t("notes")}</label><textarea class="input" id="mn" rows="3">${esc(m.notes || "")}</textarea><p class="hint">${t("notesHint")}</p>
    <label class="f">${t("tags")}</label><input class="input" id="mg" value="${esc((m.tags || []).join(", "))}" placeholder="canta, yeni">`,
  { title: m.title || L("Medya", "Media"), foot: `<button class="btn danger sq" id="md">${ic("x")}</button><button class="btn" id="ms">${t("save")}</button><button class="btn primary" id="mc">${ic("sparkle")} ${L("İçerik üret", "Create post")}</button>` });
  const data = () => ({ title: $("#mt", box).value, notes: $("#mn", box).value, tags: $("#mg", box).value.split(",").map((x) => x.trim()).filter(Boolean) });
  $("#ms", box).onclick = async () => { try { const r = await api("api/media/" + id, { method: "PATCH", body: data() }); MEDIA.set(id, { ...m, ...r }); toast(t("saved")); snd("select"); closeSheet(); render(); } catch (e) { fail(e); } };
  $("#mc", box).onclick = async () => { try { await api("api/media/" + id, { method: "PATCH", body: data() }); newPostSheet([id]); } catch (e) { fail(e); } };
  $("#md", box).onclick = async () => { if (!confirm(L("Silinsin mi?", "Delete?"))) return; try { await api("api/media/" + id, { method: "DELETE" }); MEDIA.delete(id); snd("stop"); closeSheet(); render(); } catch (e) { fail(e); } };
}

// Upload: images are cropped to an Instagram ratio and re-encoded as JPEG in the browser
// (Instagram only accepts JPEG). Videos go up as they are.
async function uploadFlow(files) {
  for (const f of files) {
    try {
      if (f.type.startsWith("image/")) await uploadImage(f);
      else if (f.type.startsWith("video/")) await uploadVideo(f);
      else toast(L(`${f.name}: desteklenmeyen dosya`, `${f.name}: unsupported file`), "err");
    } catch (e) { if (e && e.message !== "cancel") fail(e); }
  }
  await loadMedia(true); render(); refreshState();
}
function askMeta(previewHtml, name, extraHtml = "") {
  return new Promise((resolve, reject) => {
    const stem = name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").slice(0, 80);
    const box = sheet(`${previewHtml}${extraHtml}<label class="f">${t("title")}</label><input class="input" id="ut" value="${esc(/^(img|dsc|pxl|vid|whatsapp)/i.test(stem) ? "" : stem)}" placeholder="${L("örn. Siyah Deri Çanta", "e.g. Black Leather Bag")}">
      <label class="f">${t("notes")}</label><textarea class="input" id="un" rows="3" placeholder="${L("örn. Hakiki dana derisi. İç cebi var. 14 inç laptop sığar.", "e.g. Full-grain leather. Inner pocket. Fits a 14-inch laptop.")}"></textarea><p class="hint">${t("notesHint")}</p>
      <label class="f">${t("tags")}</label><input class="input" id="ug" placeholder="canta, yeni">`,
    { title: name, foot: `<button class="btn" data-close>${t("cancel")}</button><button class="btn primary" id="uGo">${ic("plus")} ${L("Yükle", "Upload")}</button>`, onClose: () => reject(new Error("cancel")) });
    $("#uGo", box).onclick = () => { const v = { title: $("#ut", box).value, notes: $("#un", box).value, tags: $("#ug", box).value, box }; sheetClose = null; resolve(v); };
  });
}
async function loadBitmap(file) {
  try { return await createImageBitmap(file, { imageOrientation: "from-image" }); }
  catch { return await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error(L("Görsel açılamadı", "Can't open image"))); i.src = URL.createObjectURL(file); }); }
}
async function uploadImage(file) {
  const bmp = await loadBitmap(file);
  const iw = bmp.width, ih = bmp.height, r0 = iw / ih;
  const RATIOS = [["4:5", 4 / 5], ["1:1", 1], ["9:16", 9 / 16], [t("original"), r0]];
  let ratio = r0 >= 0.8 && r0 <= 1 ? r0 : 4 / 5, off = { x: 0.5, y: 0.5 };
  const extra = `<div class="seg" id="rs" style="margin:6px 0">${RATIOS.map(([n, v], i) => `<button data-i="${i}" aria-pressed="${Math.abs(v - ratio) < 0.001 && (i < 3 || ratio === r0)}">${n}${i === 0 ? " · " + t("suggested") : ""}</button>`).join("")}</div><p class="hint">${L("Sürükleyerek kadrajı kaydırın. Akışta 4:5, hikâyede 9:16 en iyi görünür.", "Drag to reframe. 4:5 is best in the feed, 9:16 for Stories.")}</p>`;
  const meta = askMeta(`<div class="crop" id="cropBox"><canvas id="cropCv"></canvas></div>`, file.name, extra);
  const box = $(".sheet");
  const cv = $("#cropCv", box), g = cv.getContext("2d");
  const rect = () => {
    let w = iw, h = iw / ratio;
    if (h > ih) { h = ih; w = ih * ratio; }
    return { w, h, x: (iw - w) * off.x, y: (ih - h) * off.y };
  };
  const draw = () => {
    const r = rect();
    const maxW = Math.min(box.clientWidth - 32, 420);
    cv.width = Math.round(maxW * devicePixelRatio); cv.height = Math.round(maxW / ratio * devicePixelRatio);
    cv.parentElement.style.width = maxW + "px"; cv.parentElement.style.aspectRatio = String(ratio);
    g.drawImage(bmp, r.x, r.y, r.w, r.h, 0, 0, cv.width, cv.height);
  };
  draw();
  $("#rs", box).onclick = (e) => { const b = e.target.closest("[data-i]"); if (!b) return; ratio = RATIOS[+b.dataset.i][1]; $$("[data-i]", $("#rs", box)).forEach((x) => x.setAttribute("aria-pressed", String(x === b))); off = { x: 0.5, y: 0.5 }; draw(); snd("tap"); };
  let drag = null;
  cv.onpointerdown = (e) => { drag = { x: e.clientX, y: e.clientY, o: { ...off } }; cv.setPointerCapture(e.pointerId); };
  cv.onpointermove = (e) => {
    if (!drag) return;
    const r = rect(), sc = r.w / cv.clientWidth;
    const fx = iw - r.w > 1 ? (drag.x - e.clientX) * sc / (iw - r.w) : 0, fy = ih - r.h > 1 ? (drag.y - e.clientY) * sc / (ih - r.h) : 0;
    off = { x: Math.min(1, Math.max(0, drag.o.x + fx)), y: Math.min(1, Math.max(0, drag.o.y + fy)) }; draw();
  };
  cv.onpointerup = () => { drag = null; };
  const info = await meta;
  const r = rect();
  const outW = Math.min(1080, Math.round(r.w)), outH = Math.round(outW / ratio);
  const c = document.createElement("canvas"); c.width = outW; c.height = outH;
  c.getContext("2d").drawImage(bmp, r.x, r.y, r.w, r.h, 0, 0, outW, outH);
  const blob = await new Promise((res) => c.toBlob(res, "image/jpeg", 0.9));
  const fd = new FormData();
  fd.append("file", blob, file.name.replace(/\.[^.]+$/, "") + ".jpg");
  fd.append("title", info.title); fd.append("notes", info.notes); fd.append("tags", info.tags);
  await sendUpload(fd);
}
async function uploadVideo(file) {
  if (file.size > 100 * 1024 * 1024) throw new Error(L("Video 100 MB'tan büyük.", "Video is larger than 100 MB."));
  const url = URL.createObjectURL(file);
  const vm = await new Promise((res) => {
    const v = document.createElement("video");
    Object.assign(v, { preload: "auto", muted: true, playsInline: true });
    let meta = { w: 0, h: 0, d: 0, poster: null };
    v.onloadedmetadata = () => { meta = { ...meta, w: v.videoWidth, h: v.videoHeight, d: v.duration }; v.currentTime = Math.min(1, (v.duration || 2) / 3); };
    // One frame as the thumbnail, so lists don't have to download whole videos.
    v.onseeked = () => {
      try {
        const c = document.createElement("canvas"); const sc = 360 / (v.videoWidth || 360);
        c.width = 360; c.height = Math.round((v.videoHeight || 640) * sc);
        c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
        c.toBlob((b) => res({ ...meta, poster: b }), "image/jpeg", 0.8);
      } catch { res(meta); }
    };
    v.onerror = () => res(meta);
    setTimeout(() => res(meta), 6000);
    v.src = url;
  });
  const warn = vm.d > 90 ? L("90 saniyeden uzun: Reels için 7–30 sn daha iyi sonuç verir.", "Longer than 90 s: 7–30 s works better for Reels.") : vm.w && vm.w / vm.h > 0.7 ? L("Dikey değil: Reels ve hikâye için 9:16 çekim önerilir.", "Not vertical: shoot 9:16 for Reels and Stories.") : "";
  const info = await askMeta(`<video src="${url}" controls playsinline style="width:100%;max-height:44vh;border-radius:12px;background:#000"></video><p class="hint">${vm.w}×${vm.h} · ${nf(vm.d, 1)} sn</p>${warn ? `<div class="finding warn">${ic("warn")}<span>${warn}</span></div>` : ""}`, file.name);
  const fd = new FormData();
  fd.append("file", file, file.name); fd.append("title", info.title); fd.append("notes", info.notes); fd.append("tags", info.tags);
  fd.append("width", String(vm.w || 0)); fd.append("height", String(vm.h || 0)); fd.append("duration", String(vm.d || 0));
  if (vm.poster) fd.append("poster", vm.poster, "poster.jpg");
  await sendUpload(fd);
}
async function sendUpload(fd) {
  const btn = $("#uGo"); if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spin" style="width:18px;height:18px;border-width:2px"></span>'; }
  await api("api/media", { body: fd });
  snd("upload"); closeSheet(); toast(L("Kütüphaneye eklendi", "Added to the library"), "ok");
}

// ------------------------------------------------------------------ ANALYSIS
const PILLAR_KEYS = ["urun", "surec", "ipucu", "topluluk", "kampanya", "kanit"];
async function viewAnalysis(q) {
  await loadMedia();
  const days = +(q.get("g") || 30);
  const a = await api("api/analytics?days=" + days);
  const tt = a.totals, ch = a.change;
  const delta = (k) => ch[k] == null ? "" : `<span class="delta ${ch[k] >= 0 ? "up" : "down"}">${ch[k] >= 0 ? "▲" : "▼"} ${pct(Math.abs(ch[k]), 0)}</span>`;
  const stat = (k, label, v) => `<div class="kpi"><b data-count="${Math.round(v)}">${nf(v)}</b><span>${label} ${delta(k)}</span></div>`;
  const inter = tt.likes + tt.comments + tt.saves + tt.shares;
  const fmts = Object.entries(a.by_format).filter(([k]) => k !== "story");
  const maxR = Math.max(1, ...fmts.map(([, v]) => v.reach));
  const pil = Object.entries(a.by_pillar).filter(([k]) => PILLAR_KEYS.includes(k)).sort((x, y) => y[1].score - x[1].score);
  const vals = a.heatmap.flat().filter((x) => x != null), hmax = Math.max(1e-9, ...vals);
  const heat = `<div class="heat"><span></span>${[...Array(24)].map((_, h) => `<span class="h">${h % 3 === 0 ? h : ""}</span>`).join("")}${a.heatmap.map((row, w) => `<span>${(LANG === "tr" ? ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"] : ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])[w]}</span>${row.map((v, h) => `<i title="${h}:00" style="${v != null ? `background:color-mix(in srgb,var(--accent) ${Math.round(15 + 85 * v / hmax)}%,var(--line2))` : ""}"></i>`).join("")}`).join("")}</div>`;
  const slots = Object.entries(a.best_slots).map(([w, hs]) => `<span class="chip">${(LANG === "tr" ? ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"] : ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])[w]} ${hs.map((h) => h + ":00").join(", ")}</span>`).join("");
  return `<div class="row wrap" style="justify-content:space-between;margin-bottom:12px"><div class="seg" id="rangeSeg">${[7, 30, 90].map((d) => `<button data-v="${d}" aria-pressed="${d === days}">${d} ${L("gün", "days")}</button>`).join("")}</div><small>${L("Önceki dönemle karşılaştırma", "vs. previous period")}</small></div>
    <div class="kpis" style="margin-top:0">${stat("reach", t("reach"), tt.reach)}${stat("posts", L("Paylaşım", "Posts"), tt.posts)}${`<div class="kpi"><b>${nf(inter)}</b><span>${t("interactions")}</span></div>`}${stat("follows", L("Yeni takipçi", "New followers"), tt.follows)}${stat("shares", t("shares"), tt.shares)}${stat("saves", t("saves"), tt.saves)}${stat("profile_visits", L("Profil ziyareti", "Profile visits"), tt.profile_visits)}${stat("avg_reach", L("Ort. erişim", "Avg reach"), tt.avg_reach)}</div>
    ${a.series ? `<div class="section"><h2>${L("Günlük erişim", "Daily reach")}</h2></div><div class="card">${lineChart(a.series)}<div class="legend"><span><i></i>${L(`Son ${days} gün`, `Last ${days} days`)}</span><span><i class="p"></i>${L("Önceki dönem", "Previous period")}</span></div></div>` : ""}
    <div class="section"><h2>${L("Tellal ne diyor?", "What Tellal sees")}</h2></div><div class="card" style="padding:4px 18px"><ul class="advice">${a.advice.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
    <div class="cols"><div><div class="section"><h2>${L("Biçime göre ortalama erişim", "Average reach by format")}</h2></div><div class="card"><div class="bars">${fmts.map(([k, v]) => `<div class="bar"><span>${t(k)} <small>(${v.count})</small></span><span class="track"><i class="${v.reach === maxR ? "hi" : ""}" style="width:${Math.round(100 * v.reach / maxR)}%"></i></span><b class="num">${nf(v.reach)}</b></div>`).join("") || `<small>–</small>`}</div>
      <p class="hint">${L("Gönderilme ve kaydetme oranı erişime bölünerek karşılaştırılır; ham beğeni sayısı yanıltır.", "Sends and saves are compared per reach; raw likes mislead.")}</p></div>
      <div class="section"><h2>${L("Konulara göre", "By topic")}</h2></div><div class="card"><table class="t"><tr><th>${L("Konu", "Topic")}</th><th class="r">${L("Adet", "Posts")}</th><th class="r">${t("reach")}</th><th class="r">${t("shares")}</th><th class="r">${t("saves")}</th></tr>${pil.map(([k, v]) => `<tr><td>${t("p_" + k)}</td><td class="r num">${v.count}</td><td class="r num">${nf(v.reach)}</td><td class="r num">${pct(v.send)}</td><td class="r num">${pct(v.save)}</td></tr>`).join("")}</table></div></div>
    <div><div class="section"><h2>${L("Saat haritası", "Best times")}</h2></div><div class="card">${heat}<p class="hint">${a.learned ? L("Koyu kareler: sizin hesabınızda daha iyi sonuç alan gün/saatler.", "Darker: days and hours that worked best for you.") : L("Henüz yeterli veri yok; plan genel saatleri kullanıyor.", "Not enough data yet; the plan uses general hours.")}</p><div class="chips" style="margin-top:8px">${slots}</div></div>
      <div class="section"><h2>${L("En iyi paylaşımlar", "Top posts")}</h2></div><div class="card"><div class="list">${a.top.map((p) => `<button class="item" data-open="${p.id}">${thumb(p.media_ids[0], p.format)}<span class="grow"><b class="num">${nf(p.reach)}</b> ${t("reach").toLowerCase()} · ${t(p.format)}<br><small class="ellipsis">${esc(p.caption.split("\n")[0])}</small></span><small class="num">${t("shares")} ${pct(p.send)}</small></button>`).join("") || `<small>–</small>`}</div></div></div></div>`;
}
ROUTES[4].after = () => { const s = $("#rangeSeg"); if (s) s.onclick = (e) => { const b = e.target.closest("[data-v]"); if (b) { snd("tap"); location.hash = "#/analiz?g=" + b.dataset.v; } }; };

// ------------------------------------------------------------------ ADS
async function viewAds() {
  await loadMedia();
  const a = await api("api/ads");
  const items = a.items.length ? a.items.map((it) => `<div class="card"><div class="row" style="align-items:flex-start">${thumb(it.media_ids[0], it.format)}<div class="grow"><div class="row wrap" style="gap:6px"><span class="pill published">${L(`ortalamanın ${nf(it.ratio, 1)} katı`, `${nf(it.ratio, 1)}× your median`)}</span><span class="pill">${t(it.format)}</span></div><p class="clamp2" style="margin:6px 0 4px">${esc(it.caption.split("\n")[0])}</p><small>${esc(it.why.join(" · "))}</small></div></div>
      ${it.blocked ? `<div class="finding error" style="margin-top:10px">${ic("err")}<span>${L("Açıklamada doldurulmamış alan var; öne çıkarmadan önce düzeltin.", "Caption has a placeholder; fix it before boosting.")}</span></div>` : ""}
      <div class="tiers">${it.tiers.map((tr, i) => `<div class="tier ${i === 1 ? "mid" : ""}"><div class="eyebrow">${esc(tr.name)} · ${tr.days} ${L("gün", "days")}</div><b class="num">${money(tr.total)}</b><small>${money(tr.daily)}/${L("gün", "day")} + %5</small><small style="margin-top:6px">${L("Tahmini erişim", "Est. reach")}<br><b class="num" style="font-size:13.5px">${nf(tr.reach[0])}–${nf(tr.reach[1])}</b></small></div>`).join("")}</div>
      <div class="row wrap" style="margin-top:12px"><button class="btn sm" data-open="${it.post_id}">${L("Gönderiyi aç", "Open post")}</button><span class="hint">${L("Amaç", "Goal")}: ${esc({ messages: L("mesaj", "messages"), visits: L("ziyaret", "visits"), traffic: L("site trafiği", "traffic"), reach: L("erişim", "reach") }[it.goal])}</span></div></div>`).join("")
    : `<div class="empty">${ic("bolt")}<h3>${L("Şimdilik öneri yok", "No suggestions yet")}</h3><p>${esc(a.note || L("Ortalamanın belirgin üstünde performans gösteren bir gönderi çıkınca burada önereceğim.", "When a post clearly beats your average, it shows up here."))}</p></div>`;
  return `<div class="note"><b>${L("Tellal para harcamaz.", "Tellal never spends money.")}</b> ${L("Organik olarak zaten iyi giden gönderiyi öne çıkarmak en ucuz erişim yoludur. Aşağıdakiler öneridir; uygulamak sizin elinizde.", "Boosting a post that already works organically is the cheapest reach. These are suggestions; you decide.")}</div>
    <div class="section"><h2>${L("Öne çıkarmaya değer", "Worth boosting")}</h2></div><div class="stack">${items}</div>
    <div class="cols"><div><div class="section"><h2>${L("Bütçe hesaplayıcı", "Budget calculator")}</h2></div><div class="card" id="calc">
      <div class="seg" id="cf">${["reel", "post", "story"].map((f, i) => `<button data-v="${f}" aria-pressed="${i === 0}">${t(f)}</button>`).join("")}</div>
      <label class="f">${L("Günlük bütçe", "Daily budget")}: <b id="cdv">200</b> TL</label><input type="range" id="cd" min="50" max="2000" step="50" value="200">
      <label class="f">${L("Süre", "Duration")}: <b id="cnv">5</b> ${L("gün", "days")}</label><input type="range" id="cn" min="1" max="30" value="5">
      <div id="cout" style="margin-top:12px"></div></div></div>
    <div>${a.targeting ? `<div class="section"><h2>${L("Hedefleme önerisi", "Targeting")}</h2></div><div class="card"><ul style="margin:0;padding-left:20px">${a.targeting.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>` : ""}
    <div class="section"><h2>${L("Bilmeniz gerekenler", "Good to know")}</h2></div><div class="card"><ul style="margin:0;padding-left:20px;font-size:13.5px">${(a.notes || []).map((x) => `<li style="margin:6px 0">${esc(x)}</li>`).join("")}</ul></div></div></div>`;
}
ROUTES[5].after = () => {
  let fmt = "reel";
  const out = async () => {
    const d = +$("#cd").value, n = +$("#cn").value;
    $("#cdv").textContent = d; $("#cnv").textContent = n;
    try {
      const e = await api(`api/ads/estimate?format=${fmt}&daily=${d}&days=${n}`);
      $("#cout").innerHTML = `<div class="grid g2"><div class="stat"><b class="num">${money(e.total)}</b><span>${L("Toplam (%5 konum ücreti dahil)", "Total (incl. 5% location fee)")}</span></div><div class="stat"><b class="num">${nf(e.reach[0])}–${nf(e.reach[1])}</b><span>${L("Tahmini tekil erişim", "Est. unique reach")}</span></div></div><p class="hint">${L(`Gösterim: ${nf(e.impressions[0])}–${nf(e.impressions[1])} · BGM ${e.cpm[0]}–${e.cpm[1]} TL. KDV ayrıca beyan edilir.`, `Impressions: ${nf(e.impressions[0])}–${nf(e.impressions[1])} · CPM ${e.cpm[0]}–${e.cpm[1]} TRY. VAT is declared separately.`)}</p>`;
    } catch (er) { fail(er); }
  };
  let tmr;
  $("#cd").oninput = $("#cn").oninput = () => { $("#cdv").textContent = $("#cd").value; $("#cnv").textContent = $("#cn").value; clearTimeout(tmr); tmr = setTimeout(out, 150); };
  $("#cf").onclick = (e) => { const b = e.target.closest("[data-v]"); if (!b) return; fmt = b.dataset.v; $$("#cf [data-v]").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); snd("tap"); out(); };
  out();
};

// ------------------------------------------------------------------ COMMENTS
async function viewComments(q) {
  await loadMedia();
  const st = q.get("s") || "open";
  const list = await api("api/comments" + (st === "all" ? "" : "?status=" + st));
  const tabs = `<div class="seg" id="cs" style="margin-bottom:12px">${[["open", L("Yanıt bekleyen", "To answer")], ["replied", L("Yanıtlanan", "Answered")], ["spam", "Spam"], ["all", L("Tümü", "All")]].map(([k, n]) => `<button data-v="${k}" aria-pressed="${k === st}">${n}</button>`).join("")}</div>`;
  if (!list.length) return tabs + `<div class="empty">${ic("chat")}<h3>${L("Burada yorum yok", "No comments here")}</h3><p>${L("Yeni yorumlar her 15 dakikada bir alınır ve niyetine göre sınıflanır.", "New comments are fetched every 15 minutes and sorted by intent.")}</p></div>`;
  return tabs + `<p class="hint" style="margin-top:0">${L("Taslaklar hazır; hiçbir yanıt siz göndermeden gitmez. Şikâyetlere şablon yazılmaz.", "Drafts are ready; nothing is sent until you send it. Complaints never get a template.")}</p><div class="card">${list.map((c) => `<div class="cmt" data-c="${c.id}"><div class="row">${c.post ? thumb(c.post.media_ids[0], null, "thumb sq") : ""}<div class="grow"><div class="row wrap" style="gap:6px"><span class="who">@${esc(c.username || "?")}</span><span class="pill ${c.intent === "sikayet" ? "failed" : c.intent === "fiyat" || c.intent === "siparis" || c.intent === "stok" ? "pending" : c.intent === "spam" ? "warn" : ""}">${esc(c.label)}</span><small>${relDay(c.ts)} ${hm(c.ts)}</small></div><div class="text">${esc(c.text)}</div></div></div>
    ${c.status === "replied" ? `<div class="finding info">${ic("check")}<span>${esc(c.reply_text)}</span></div>`
      : c.intent === "sikayet" ? `<div class="finding error">${ic("warn")}<span>${L("Şikâyet: kişisel olarak ve hızlıca DM'den ilgilenin; herkese açık tartışmaya girmeyin.", "Complaint: handle it personally via DM, quickly; don't argue in public.")}</span></div><textarea class="input" rows="2" placeholder="${L("Kısa, özür dileyen bir yanıt (isteğe bağlı)", "A short apology (optional)")}">${esc(c.reply_draft || "")}</textarea><div class="row" style="margin-top:8px;justify-content:flex-end"><button class="btn sm" data-act="ignored">${L("Kapat", "Close")}</button><button class="btn sm primary" data-act="send">${ic("send")} ${L("Yanıtla", "Reply")}</button></div>`
      : `<textarea class="input" rows="2">${esc(c.reply_draft || "")}</textarea><div class="saved" data-saved="${esc(c.username || "")}"></div><div class="row" style="margin-top:8px;justify-content:flex-end"><button class="btn sm" data-act="${c.intent === "spam" ? "spam" : "ignored"}">${c.intent === "spam" ? L("Spam olarak bırak", "Keep as spam") : L("Yoksay", "Ignore")}</button><button class="btn sm primary" data-act="send">${ic("send")} ${L("Yanıtla", "Reply")}</button></div>`}</div>`).join("")}</div>`;
}
ROUTES[6].after = () => {
  const cs = $("#cs"); if (cs) cs.onclick = (e) => { const b = e.target.closest("[data-v]"); if (b) { snd("tap"); location.hash = "#/yorumlar?s=" + b.dataset.v; } };
  $$(".cmt").forEach((el) => el.onclick = async (e) => {
    const b = e.target.closest("[data-act]"); if (!b) return;
    const id = +el.dataset.c, ta = $("textarea", el);
    try {
      if (ta) await api("api/comments/" + id, { method: "PATCH", body: { reply_draft: ta.value } });
      if (b.dataset.act === "send") { await api(`api/comments/${id}/send`, { body: {} }); toast(L("Yanıt gönderildi", "Reply sent"), "ok"); snd("success"); }
      else { await api("api/comments/" + id, { method: "PATCH", body: { status: b.dataset.act } }); snd("select"); }
      el.classList.add("done");
      setTimeout(() => { el.remove(); refreshState(); if (!$(".cmt")) render(); }, 350);
    } catch (er) { fail(er); }
  });
  paintSaved();
};
// Saved replies: the owner's own wording, one tap away. {user} becomes the commenter's name.
const DEFAULT_REPLIES = () => [
  L("Merhaba {user}! Detayları DM'den ilettik 🙏", "Hi {user}! We've sent the details by DM 🙏"),
  L("Çok teşekkür ederiz {user} 🤍", "Thank you so much {user} 🤍"),
  L("{user} stok durumunu hemen kontrol edip yazıyoruz.", "{user} we'll check stock and get back to you."),
];
function paintSaved() {
  const list = store.get("replies", null) || DEFAULT_REPLIES();
  $$("[data-saved]").forEach((box) => {
    box.innerHTML = list.map((r, i) => `<button class="chip suggest" data-r="${i}" title="${esc(r)}">${esc((() => { const x = r.replace("{user}", "").replace(/\s+/g, " ").trim(); return x.length > 34 ? x.slice(0, 32) + "…" : x; })())}</button>`).join("")
      + `<button class="chip suggest" data-rsave>${ic("plus")} ${L("Bu yanıtı kaydet", "Save this reply")}</button>`;
    box.onclick = (e) => {
      const ta = box.previousElementSibling, user = box.dataset.saved ? "@" + box.dataset.saved : "";
      const r = e.target.closest("[data-r]");
      if (r) { ta.value = list[+r.dataset.r].replace("{user}", user).replace(/\s+/g, " ").trim(); grow(ta); ta.focus(); snd("tap"); return; }
      if (e.target.closest("[data-rsave]")) {
        const v = ta.value.trim().replace(user, "{user}");
        if (!v) return;
        const next = [v, ...list.filter((x) => x !== v)].slice(0, 8);
        store.set("replies", next); toast(L("Hazır yanıtlara eklendi", "Saved to your replies"), "ok"); snd("select"); paintSaved();
      }
    };
  });
}

// ------------------------------------------------------------------ BRAND
let BR = null;
async function viewBrand() {
  const r = await api("api/brand");
  BR = r.brand;
  const b = BR, sec = r.sectors;
  const tones = [["samimi", L("Samimi", "Warm")], ["profesyonel", L("Profesyonel", "Professional")], ["eglenceli", L("Eğlenceli", "Playful")], ["zarif", L("Zarif", "Elegant")], ["sade", L("Sade", "Plain")]];
  const langs = [["tr", "Türkçe"], ["en", "English"], ["sr", "Srpski"], ["hr", "Hrvatski"], ["ro", "Română"]];
  const ctas = [["dm", "DM"], ["whatsapp", "WhatsApp"], ["link", L("Biyografideki link", "Link in bio")], ["visit", L("Mağaza ziyareti", "Store visit")], ["call", L("Telefon", "Phone")]];
  const goals = [["satis", L("Satış", "Sales")], ["bilinirlik", L("Bilinirlik", "Awareness")], ["topluluk", L("Topluluk", "Community")]];
  const step = (k, v, max) => `<div class="stepper" data-k="${k}" data-max="${max}"><button data-d="-1">−</button><span class="num">${v}</span><button data-d="1">+</button></div>`;
  return `<div class="cols"><div>
    <div class="card"><h3>${L("İşletme", "Business")}</h3>
      <label class="f">${L("Marka adı", "Brand name")}</label><input class="input" data-f="name" value="${esc(b.name)}">
      <div class="grid g2"><div><label class="f">${L("Instagram kullanıcı adı", "Instagram handle")}</label><input class="input" data-f="handle" value="${esc(b.handle)}"></div><div><label class="f">${L("Şehir", "City")}</label><input class="input" data-f="city" value="${esc(b.city)}"></div></div>
      <label class="f">${L("Sektör", "Sector")}</label><select class="input" data-f="sector">${Object.entries(sec).map(([k, v]) => `<option value="${k}" ${k === b.sector ? "selected" : ""}>${esc(v)}</option>`).join("")}</select>
      <label class="f">${L("Kısa tanım", "Short description")}</label><textarea class="input" data-f="description" rows="2">${esc(b.description)}</textarea>
      <label class="f">${L("Hedef kitle", "Audience")}</label><input class="input" data-f="audience" value="${esc(b.audience)}"></div>
    <div class="card"><h3>${L("Ses ve dil", "Voice and language")}</h3>
      <label class="f">${L("Ton", "Tone")}</label><div class="chips" data-one="tone">${tones.map(([k, n]) => `<button class="chip" data-v="${k}" aria-pressed="${b.tone === k}">${n}</button>`).join("")}</div>
      <label class="f">Emoji</label><div class="seg" data-one="emoji">${[[0, L("Yok", "None")], [1, L("Az", "Some")], [2, L("Bol", "Lots")]].map(([k, n]) => `<button data-v="${k}" aria-pressed="${b.emoji === k}">${n}</button>`).join("")}</div>
      <label class="f">${L("İçerik dilleri (ilki varsayılan)", "Content languages (first is default)")}</label><div class="chips" data-many="languages">${langs.map(([k, n]) => `<button class="chip" data-v="${k}" aria-pressed="${b.languages.includes(k)}">${n}</button>`).join("")}</div></div>
    <div class="card"><h3>${L("Ne satıyorsunuz?", "What you sell")}</h3>
      <label class="f">${L("Öne çıkan özellikler (her satıra bir)", "Selling points (one per line)")}</label><textarea class="input" data-f="usps" data-list rows="3">${esc(b.usps.join("\n"))}</textarea>
      <label class="f">${L("Ürünler ve fiyatlar", "Products and prices")}</label><div id="prods">${b.products.map((p) => prodRow(p)).join("")}</div><button class="btn sm" id="addProd" style="margin-top:6px">${ic("plus")} ${L("Ürün ekle", "Add product")}</button>
      <p class="hint">${L("Fiyat yazarsanız ilgili gönderilerde ve fiyat soran yorumlara yanıtta kullanılır; yazmazsanız Tellal fiyat uydurmaz.", "Prices are used in posts and price replies; if empty, Tellal never makes one up.")}</p></div>
  </div><div>
    <div class="card"><h3>${L("İletişim", "Contact")}</h3>
      <label class="f">${L("Müşteri nereden ulaşsın?", "How should customers reach you?")}</label><div class="chips" data-one="cta">${ctas.map(([k, n]) => `<button class="chip" data-v="${k}" aria-pressed="${b.cta === k}">${n}</button>`).join("")}</div>
      <div class="grid g2"><div><label class="f">WhatsApp</label><input class="input" data-f="whatsapp" value="${esc(b.whatsapp)}" inputmode="tel"></div><div><label class="f">${L("Telefon", "Phone")}</label><input class="input" data-f="phone" value="${esc(b.phone)}" inputmode="tel"></div></div>
      <label class="f">${L("Adres", "Address")}</label><input class="input" data-f="address" value="${esc(b.address)}"><label class="f">Link</label><input class="input" data-f="link" value="${esc(b.link)}" inputmode="url"></div>
    <div class="card"><h3>${L("Paylaşım ritmi", "Posting rhythm")}</h3>
      <div class="spread" style="margin-top:10px"><span>${L("Haftalık gönderi", "Posts per week")}</span>${step("posts_per_week", b.rhythm.posts_per_week, 14)}</div>
      <div class="spread" style="margin-top:10px"><span>${L("Haftalık Reels", "Reels per week")}</span>${step("reels_per_week", b.rhythm.reels_per_week, 14)}</div>
      <div class="spread" style="margin-top:10px"><span>${L("Günlük hikâye", "Stories per day")}</span>${step("stories_per_day", b.rhythm.stories_per_day, 6)}</div>
      <div class="spread" style="margin-top:10px"><span>${L("Sessiz saatler", "Quiet hours")}</span><span class="row"><input class="input" type="number" min="0" max="23" data-r="quiet_start" value="${b.rhythm.quiet_start}" style="width:72px"> – <input class="input" type="number" min="0" max="23" data-r="quiet_end" value="${b.rhythm.quiet_end}" style="width:72px"></span></div>
      <p class="hint">${L("Küçük hesaplar için haftada 3–5 akış paylaşımı ve 2–3 Reels, düzenli olduğu sürece yeterlidir. Süreklilik sıklıktan önemlidir.", "For small accounts, 3–5 feed posts and 2–3 Reels a week is plenty if it's steady. Consistency beats volume.")}</p></div>
    <div class="card"><h3>${L("Kurallar", "Rules")}</h3>
      <label class="f">${L("Marka hashtag'i", "Brand hashtag")}</label><input class="input" data-f="brand_hashtag" value="${esc(b.brand_hashtag)}" placeholder="markam">
      <label class="f">${L("Asla kullanılmayacak kelimeler", "Words never to use")}</label><input class="input" data-f="banned_words" data-csv value="${esc(b.banned_words.join(", "))}" placeholder="ucuz, imitasyon">
      <label class="f">${L("Hedefler", "Goals")}</label><div class="chips" data-many="goals">${goals.map(([k, n]) => `<button class="chip" data-v="${k}" aria-pressed="${b.goals.includes(k)}">${n}</button>`).join("")}</div>
      <label class="switch"><span>${L("Varsayılan: yapay zekâ görsel etiketi", "Default: AI visuals label")}</span><input type="checkbox" data-b="ai_label_default" ${b.ai_label_default ? "checked" : ""}></label></div>
    <div class="card"><h3>${L("Biyografi önerileri", "Bio ideas")}</h3><p class="hint">${L("Instagram, biyografinin API ile değiştirilmesine izin vermiyor. Beğendiğinizi kopyalayıp profilinize yapıştırın (en fazla 150 karakter).", "Instagram doesn't let apps change your bio. Copy one and paste it into your profile (max 150 characters).")}</p>
      <div id="bios">${bioHtml(r.bios)}</div></div>
  </div></div>
  <div style="position:sticky;bottom:calc(var(--tabs-h) + 12px + var(--safe-b));margin-top:16px;display:flex;justify-content:flex-end"><button class="btn primary" id="brandSave" style="box-shadow:var(--shadow)">${ic("check")} ${t("save")}</button></div>`;
}
const prodRow = (p = { name: "", price: "", notes: "" }) => `<div class="row prod" style="margin-top:6px"><input class="input" placeholder="${L("Ürün", "Product")}" value="${esc(p.name)}"><input class="input" placeholder="${L("Fiyat", "Price")}" value="${esc(p.price)}" style="max-width:120px"><button class="icon-btn" data-rm>${ic("x")}</button></div>`;
const bioHtml = (bios) => bios.map((x) => `<div class="card" style="box-shadow:none;background:var(--card2);padding:12px"><pre style="white-space:pre-wrap;font:inherit;margin:0">${esc(x)}</pre><div class="spread" style="margin-top:6px"><small class="num">${[...x].length}/150</small><button class="btn sm" data-copy="${esc(x)}">${ic("copy")} ${L("Kopyala", "Copy")}</button></div></div>`).join("");
ROUTES[7].after = () => {
  const v = $("#view");
  v.addEventListener("click", (e) => {
    const one = e.target.closest("[data-one] [data-v]");
    if (one) { $$("[data-v]", one.parentElement).forEach((x) => x.setAttribute("aria-pressed", String(x === one))); snd("tap"); }
    const many = e.target.closest("[data-many] [data-v]");
    if (many) { many.setAttribute("aria-pressed", String(many.getAttribute("aria-pressed") !== "true")); snd("tap"); }
    const st = e.target.closest(".stepper [data-d]");
    if (st) { const box = st.parentElement, sp = $("span", box); sp.textContent = Math.max(0, Math.min(+box.dataset.max, +sp.textContent + +st.dataset.d)); snd("tap"); }
    const rm = e.target.closest("[data-rm]"); if (rm) rm.parentElement.remove();
    const cp = e.target.closest("[data-copy]"); if (cp) copy(cp.dataset.copy);
  });
  $("#addProd").onclick = () => { $("#prods").insertAdjacentHTML("beforeend", prodRow()); snd("tap"); };
  $("#brandSave").onclick = async () => {
    const b = structuredClone(BR);
    $$("[data-f]", v).forEach((el) => { const k = el.dataset.f; b[k] = "list" in el.dataset ? el.value.split("\n").map((x) => x.trim()).filter(Boolean) : "csv" in el.dataset ? el.value.split(",").map((x) => x.trim()).filter(Boolean) : el.value.trim(); });
    $$("[data-one]", v).forEach((g) => { const on = $("[aria-pressed=true]", g); if (on) b[g.dataset.one] = g.dataset.one === "emoji" ? +on.dataset.v : on.dataset.v; });
    $$("[data-many]", v).forEach((g) => { b[g.dataset.many] = $$("[aria-pressed=true]", g).map((x) => x.dataset.v); });
    if (!b.languages.length) b.languages = ["tr"];
    if (!b.goals.length) b.goals = ["satis"];
    $$(".stepper", v).forEach((s) => (b.rhythm[s.dataset.k] = +$("span", s).textContent));
    $$("[data-r]", v).forEach((el) => (b.rhythm[el.dataset.r] = Math.max(0, Math.min(23, +el.value || 0))));
    $$("[data-b]", v).forEach((el) => (b[el.dataset.b] = el.checked));
    b.products = $$(".prod", v).map((r) => { const [n, p] = $$("input", r).map((x) => x.value.trim()); return { name: n, price: p, notes: "" }; }).filter((p) => p.name);
    try { const r = await api("api/brand", { method: "PUT", body: b }); BR = r.brand; $("#bios").innerHTML = bioHtml(r.bios); toast(t("saved"), "ok"); snd("success"); refreshState(); }
    catch (e) { fail(e); }
  };
};
async function copy(text) {
  try { await navigator.clipboard.writeText(text); }
  catch { const ta = document.createElement("textarea"); ta.value = text; document.body.append(ta); ta.select(); document.execCommand("copy"); ta.remove(); }
  toast(t("copied")); snd("select");
}

// ------------------------------------------------------------------ SETTINGS
async function viewSettings(q) {
  await refreshState();
  const st = S.state;
  if (q.get("baglandi")) toast(L("Instagram hesabı bağlandı", "Instagram connected"), "ok");
  if (q.get("hata")) toast(q.get("hata"), "err");
  const theme = store.get("theme", "auto");
  const accs = st.accounts.length ? st.accounts.map((a) => `<div class="item"><span class="ig-av" style="width:40px;height:40px"><i></i></span><span class="grow"><b>@${esc(a.username)}</b><br><small>${esc(a.provider === "demo" ? L("Demo hesap", "Demo account") : "Instagram")} · ${nf(a.followers)} ${L("takipçi", "followers")}${a.token_expires ? ` · ${L("anahtar", "token")} ${dt(a.token_expires, { day: "numeric", month: "short" })}` : ""}</small></span><button class="icon-btn" data-acc-refresh="${a.id}" title="${L("Yenile", "Refresh")}">${ic("refresh")}</button>${a.provider !== "demo" ? `<button class="icon-btn" data-acc-del="${a.id}" title="${t("del")}">${ic("x")}</button>` : ""}</div>`).join("") : `<p class="muted">${L("Bağlı hesap yok.", "No account connected.")}</p>`;
  const connect = st.mode === "instagram"
    ? (st.ig_configured ? `<a class="btn primary" href="auth/instagram/start">${ic("link")} ${L("Instagram hesabı bağla", "Connect Instagram")}</a>` : `<div class="finding warn">${ic("warn")}<span>${L("Meta uygulama bilgileri eksik: TELLAL_IG_APP_ID ve TELLAL_IG_APP_SECRET. README'deki 'Instagram bağlantısı' adımlarını izleyin.", "Meta app credentials missing: TELLAL_IG_APP_ID and TELLAL_IG_APP_SECRET. See 'Connecting Instagram' in the README.")}</span></div>`)
    : `<p class="hint">${L("Demo modundasınız. Gerçek hesap için sunucuyu TELLAL_MODE=instagram ile başlatın (README).", "You're in demo mode. For a real account, start the server with TELLAL_MODE=instagram (README).")}</p>`;
  return `<div class="cols"><div>
    <div class="card"><h3>${L("Hesaplar", "Accounts")}</h3><div class="list" style="margin:6px 0 10px">${accs}</div>${connect}</div>
    <div class="card"><h3>${L("Görünüm", "Appearance")}</h3>
      <label class="f">${t("language")}</label><div class="seg" id="langSet">${[["tr", "Türkçe"], ["en", "English"]].map(([k, n]) => `<button data-v="${k}" aria-pressed="${LANG === k}">${n}</button>`).join("")}</div>
      <label class="f">${t("theme")}</label><div class="seg" id="themeSet">${[["auto", t("auto")], ["light", t("light")], ["dark", t("dark")]].map(([k, n]) => `<button data-v="${k}" aria-pressed="${theme === k}">${n}</button>`).join("")}</div>
      <label class="switch"><span>${t("sound")}</span><input type="checkbox" id="sndSet" ${kit && kit.enabled ? "checked" : ""}></label></div>
  </div><div>
    <div class="card"><h3>${L("Nasıl çalışır, neyi yapmaz?", "How it works, and what it won't do")}</h3><ul style="padding-left:20px;font-size:13.5px;margin:8px 0 0">
      <li>${L("Hiçbir şey onayınız olmadan paylaşılmaz. Onayladıklarınız zamanı gelince otomatik paylaşılır.", "Nothing is published without your approval. Approved posts go out on time automatically.")}</li>
      <li>${L("Görsel üretmez; sizin fotoğraf ve videolarınızı kullanır. Yorum, fiyat ya da indirim uydurmaz; eksik bilgi [köşeli parantez] olarak bırakılır ve doldurulmadan onaylanamaz.", "It doesn't generate images; it uses yours. It never invents reviews, prices or discounts; missing facts stay as [placeholders] and block approval.")}</li>
      <li>${L("Biyografi ve DM'ler: Instagram biyografi değiştirmeye izin vermiyor (öneri verilir). DM yanıtları sonraki sürümde.", "Bio and DMs: Instagram doesn't allow bio changes (ideas are given). DM replies come in a later version.")}</li>
      <li>${L("Reklam vermez, para harcamaz; yalnızca öneri ve bütçe tahmini sunar.", "It never runs ads or spends money; it suggests and estimates.")}</li>
      <li>${L("Instagram, medyayı herkese açık bir adresten indirir: gerçek kullanımda sunucunun internetten erişilebilir olması gerekir (TELLAL_PUBLIC_URL).", "Instagram downloads media from a public URL: in real use the server must be reachable (TELLAL_PUBLIC_URL).")}</li></ul></div>
    <div class="card"><h3>${L("Veri ve yedek", "Data and backup")}</h3><p class="hint" style="margin:6px 0 12px">${L("Marka profili, içerikler, sonuçlar ve yorumlar tek bir JSON dosyasına yazılır. Medya dosyaları ve erişim anahtarları dahil edilmez.", "Brand profile, posts, results and comments in one JSON file. Media files and access tokens are not included.")}</p>
      <div class="row wrap"><button class="btn" id="exportBtn">${ic("download")} ${L("Yedeği indir", "Download backup")}</button><button class="btn ghost" id="keysBtn">${ic("keyboard")} ${L("Klavye kısayolları", "Keyboard shortcuts")}</button></div></div>
    <div class="card"><h3>${L("Sistem", "System")}</h3><p class="hint" style="margin-top:6px">v${esc(st.version)} · ${st.mode === "demo" ? L("demo modu", "demo mode") : "Instagram"} · ${st.in_browser ? L("tarayıcıda çalışıyor", "running in the browser") : esc(st.public_url)} · ${L("metin motoru", "text engine")}: ${st.llm ? L("yapay zekâ modeli + şablon", "language model + templates") : L("şablon", "templates")} · ${esc(st.timezone)}</p>
      ${st.mode === "demo" ? `<button class="btn danger" id="demoReset">${ic("refresh")} ${L("Demoyu sıfırla", "Reset demo")}</button>` : ""}</div>
  </div></div>`;
}
ROUTES[8].after = () => {
  $("#langSet").onclick = (e) => { const b = e.target.closest("[data-v]"); if (!b) return; LANG = b.dataset.v; store.set("lang", LANG); document.documentElement.lang = LANG; snd("tap"); render(); };
  $("#themeSet").onclick = (e) => { const b = e.target.closest("[data-v]"); if (!b) return; store.set("theme", b.dataset.v); applyTheme(); snd("tap"); render(); };
  $("#sndSet").onchange = (e) => { kit && kit.setEnabled(e.target.checked); snd("tap"); paintNav(); };
  $("#exportBtn").onclick = async () => {
    try {
      const r = await fetch("api/export"); if (!r.ok) throw new Error(t("error"));
      const url = URL.createObjectURL(await r.blob()), a = document.createElement("a");
      const d = zoneParts(Date.now() / 1000);
      a.href = url; a.download = `tellal-yedek-${d.year}${d.month}${d.day}.json`; document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000); snd("success");
    } catch (er) { fail(er); }
  };
  $("#keysBtn").onclick = shortcutsSheet;
  const dr = $("#demoReset");
  if (dr) dr.onclick = async () => { if (!confirm(L("Demo verileri sıfırlansın mı?", "Reset demo data?"))) return; try { await api("api/demo/reset", { body: {} }); blobCache.clear(); MEDIA.clear(); toast(L("Demo yeniden hazırlandı", "Demo reset"), "ok"); go(""); } catch (er) { fail(er); } };
  $("#view").addEventListener("click", async (e) => {
    const r = e.target.closest("[data-acc-refresh]"), d = e.target.closest("[data-acc-del]");
    try {
      if (r) { await api(`api/accounts/${r.dataset.accRefresh}/refresh`, { body: {} }); toast(t("saved")); render(); }
      if (d && confirm(L("Hesap bağlantısı kaldırılsın mı?", "Disconnect this account?"))) { await api("api/accounts/" + d.dataset.accDel, { method: "DELETE" }); render(); }
    } catch (er) { fail(er); }
  });
};

// ------------------------------------------------------------------ login
function showLogin() {
  $("#view").innerHTML = `<div class="login card"><span class="logo" style="display:inline-block;width:56px;height:56px;border-radius:14px"></span><h2 style="margin:10px 0">${t("loginT")}</h2><input class="input" type="password" id="pw" placeholder="${t("password")}" autocomplete="current-password"><button class="btn primary block" id="pwGo" style="margin-top:10px">${t("login")}</button></div>`;
  const go_ = async () => { try { await api("api/login", { body: { password: $("#pw").value } }); snd("success"); await refreshState(); render(); } catch (e) { fail(e); } };
  $("#pwGo").onclick = go_;
  $("#pw").onkeydown = (e) => { if (e.key === "Enter") go_(); };
  $("#pw").focus();
}

// ------------------------------------------------------------------ boot
function applyTheme() {
  const th = store.get("theme", "auto");
  if (th === "auto") document.documentElement.removeAttribute("data-theme"); else document.documentElement.dataset.theme = th;
  const bg = getComputedStyle(document.documentElement).getPropertyValue("--bg").trim();
  $$('meta[name="theme-color"]').forEach((m) => m.setAttribute("content", bg));
}
applyTheme();
document.documentElement.lang = LANG;
// Spotlight: cards catch a soft light under the pointer.
if (matchMedia("(hover: hover)").matches) document.addEventListener("pointermove", (e) => {
  const c = e.target.closest && e.target.closest(".card,.kpi");
  if (!c) return;
  const r = c.getBoundingClientRect();
  c.style.setProperty("--mx", `${e.clientX - r.left}px`); c.style.setProperty("--my", `${e.clientY - r.top}px`);
}, { passive: true });
window.addEventListener("scroll", () => $(".top").classList.toggle("scrolled", scrollY > 4), { passive: true });
window.addEventListener("hashchange", () => { closeSheet(); if (route().id !== "kutuphane") pickMode = null; render(); });

let lastPending = null;
async function heartbeat() {
  // The server runs its own scheduler; in the browser build nothing runs in the background,
  // so the page drives it while it's open.
  try {
    if (S.state && S.state.in_browser) {
      const r = await api("api/scheduler/tick", { body: {} });
      if (r.published) { toast(L(`${r.published} içerik paylaşıldı`, `${r.published} posts published`), "ok"); snd("notify"); }
    }
    await refreshState();
    if (lastPending !== null && S.state.counts.pending > lastPending) snd("notify");
    lastPending = S.state.counts.pending;
  } catch { /* offline for a moment */ }
}

(async () => {
  try { await refreshState(); } catch (e) { if (e.message === "login") return; }
  render();
  setInterval(heartbeat, 30000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) heartbeat(); });
  if (AK && !window.pybridge) {
    AK.installHint({ app: "Tellal", accent: "#1b1b19", lang: () => LANG, bottom: 84 });
    if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {});
  }
  if ("serviceWorker" in navigator && !window.pybridge) navigator.serviceWorker.register("sw.js").catch(() => {});
})();
})();
