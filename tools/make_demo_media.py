"""Builds the demo library (illustrated product photos and short vertical videos) for a made-up workshop.

Run once; the output is committed under src/tellal/demo_media. Needs rsvg-convert and ffmpeg.
    python tools/make_demo_media.py
"""

from __future__ import annotations

import json
import math
import subprocess
import tempfile
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "src" / "tellal" / "demo_media"
W, H = 864, 1080  # 4:5

BG = {"krem": ("#f3ebe0", "#e6d8c6"), "kum": ("#efe3d3", "#d9c4a8"), "yesil": ("#e3e8df", "#c9d3c3"),
      "gri": ("#e9e7e4", "#d3cfca"), "gul": ("#f2e4e0", "#e2c9c1")}
LEATHER = {"siyah": ("#2b2726", "#141211"), "taba": ("#a8642f", "#7a4420"), "kahve": ("#6b4329", "#45291a"),
           "bordo": ("#7a2a2e", "#521a1d"), "yesil": ("#3f5a45", "#2a3d2f"), "bej": ("#c9a77f", "#a7845e")}


def frame(bg: str, body: str, w: int = W, h: int = H) -> str:
    a, b = BG[bg]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs>
 <radialGradient id="bg" cx="50%" cy="38%" r="75%"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></radialGradient>
 <filter id="sh" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="18"/></filter>
 <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="4"/><feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.06 0"/></filter>
</defs>
<rect width="100%" height="100%" fill="url(#bg)"/>
{body}
<rect width="100%" height="100%" filter="url(#grain)"/>
</svg>"""


def grad(id_: str, color: str) -> str:
    a, b = LEATHER[color]
    return f'<linearGradient id="{id_}" x1="0" y1="0" x2="0.4" y2="1"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>'


def stitch(d: str, color: str = "#e9d9bf") -> str:
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="3" stroke-dasharray="10 8" stroke-linecap="round" opacity="0.85"/>'


def shadow(cx: float, cy: float, rx: float, ry: float) -> str:
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#000" opacity="0.22" filter="url(#sh)"/>'


def tote(color: str, bg: str) -> str:
    body = f"""<defs>{grad('g', color)}</defs>
{shadow(432, 900, 270, 34)}
<path d="M300 380 C300 220 564 220 564 380" fill="none" stroke="{LEATHER[color][1]}" stroke-width="26" stroke-linecap="round"/>
<path d="M330 380 C330 260 534 260 534 380" fill="none" stroke="{LEATHER[color][0]}" stroke-width="10" opacity="0.5"/>
<path d="M190 380 L674 380 L640 890 L224 890 Z" fill="url(#g)"/>
<path d="M190 380 L674 380 L668 470 L196 470 Z" fill="#fff" opacity="0.06"/>
{stitch('M214 404 L650 404')}{stitch('M232 866 L632 866')}
<rect x="402" y="440" width="60" height="38" rx="6" fill="#c9a24b"/><rect x="414" y="450" width="36" height="18" rx="3" fill="#8f6d27"/>
<path d="M250 420 L236 860" stroke="#fff" stroke-width="22" opacity="0.05"/>"""
    return frame(bg, body)


def wallet(color: str, bg: str) -> str:
    body = f"""<defs>{grad('g', color)}</defs>
{shadow(432, 760, 250, 30)}
<g transform="rotate(-8 432 560)">
<rect x="192" y="380" width="480" height="350" rx="26" fill="url(#g)"/>
<path d="M192 470 Q432 560 672 470 L672 406 Q672 380 646 380 L218 380 Q192 380 192 406 Z" fill="{LEATHER[color][1]}" opacity="0.9"/>
{stitch('M214 400 L650 400 M214 710 L650 710 M210 404 L210 706 M654 404 L654 706')}
<circle cx="432" cy="520" r="16" fill="#c9a24b"/><circle cx="432" cy="520" r="7" fill="#8f6d27"/>
</g>"""
    return frame(bg, body)


def belt(color: str, bg: str) -> str:
    pts = []
    for i in range(0, 361, 6):
        t = math.radians(i)
        pts.append(f"{432 + 230 * math.cos(t):.1f},{540 + 150 * math.sin(t):.1f}")
    body = f"""<defs>{grad('g', color)}</defs>
{shadow(432, 760, 260, 28)}
<polyline points="{' '.join(pts)}" fill="none" stroke="url(#g)" stroke-width="64" stroke-linejoin="round"/>
<polyline points="{' '.join(pts)}" fill="none" stroke="#e9d9bf" stroke-width="3" stroke-dasharray="10 8" opacity="0.6" transform="translate(0 -22)"/>
<rect x="620" y="480" width="70" height="120" rx="14" fill="none" stroke="#c9a24b" stroke-width="14"/>
<rect x="648" y="470" width="10" height="140" rx="4" fill="#b28d3d"/>"""
    return frame(bg, body)


def cardholder(color: str, bg: str) -> str:
    body = f"""<defs>{grad('g', color)}</defs>
{shadow(432, 790, 200, 26)}
<rect x="270" y="300" width="300" height="190" rx="16" fill="#3b6ea8" transform="rotate(-6 420 395)"/>
<rect x="282" y="314" width="70" height="44" rx="6" fill="#d9c27a" transform="rotate(-6 420 395)"/>
<rect x="250" y="400" width="364" height="380" rx="24" fill="url(#g)"/>
<path d="M250 470 L614 470" stroke="{LEATHER[color][1]}" stroke-width="6"/>
{stitch('M270 420 L594 420 M270 760 L594 760 M268 424 L268 756 M596 424 L596 756')}
<text x="432" y="640" text-anchor="middle" font-family="Inter Display" font-size="34" fill="#e9d9bf" opacity="0.7" letter-spacing="6">L · D</text>"""
    return frame(bg, body)


def backpack(color: str, bg: str) -> str:
    body = f"""<defs>{grad('g', color)}</defs>
{shadow(432, 930, 230, 30)}
<path d="M352 270 C352 200 512 200 512 270" fill="none" stroke="{LEATHER[color][1]}" stroke-width="22" stroke-linecap="round"/>
<rect x="236" y="270" width="392" height="640" rx="90" fill="url(#g)"/>
<path d="M236 470 Q432 400 628 470 L628 360 Q628 270 538 270 L326 270 Q236 270 236 360 Z" fill="{LEATHER[color][1]}"/>
{stitch('M262 480 Q432 416 602 480')}
<rect x="318" y="600" width="228" height="200" rx="30" fill="{LEATHER[color][1]}" opacity="0.8"/>
{stitch('M336 620 L528 620')}
<rect x="410" y="470" width="44" height="70" rx="8" fill="#c9a24b"/>"""
    return frame(bg, body)


def keychain(color: str, bg: str) -> str:
    body = f"""<defs>{grad('g', color)}</defs>
{shadow(432, 820, 140, 22)}
<circle cx="432" cy="300" r="62" fill="none" stroke="#b9b5ae" stroke-width="12"/>
<rect x="420" y="352" width="24" height="70" rx="8" fill="#c9a24b"/>
<path d="M352 420 L512 420 L512 700 L432 780 L352 700 Z" fill="url(#g)"/>
{stitch('M372 440 L492 440 L492 690 L432 750 L372 690 Z')}
<circle cx="432" cy="480" r="12" fill="#e9d9bf" opacity="0.5"/>"""
    return frame(bg, body)


def workshop(bg: str) -> str:
    body = f"""<defs>{grad('g', 'taba')}{grad('k', 'kahve')}</defs>
<rect x="0" y="640" width="{W}" height="{H - 640}" fill="#8a6a4c"/>
<rect x="0" y="640" width="{W}" height="14" fill="#6f5338"/>
{shadow(430, 820, 300, 34)}
<path d="M150 560 Q430 470 720 560 L690 820 Q430 880 170 820 Z" fill="url(#g)"/>
{stitch('M190 600 Q430 520 680 600')}
<line x1="560" y1="300" x2="700" y2="700" stroke="#cfcac2" stroke-width="10" stroke-linecap="round"/>
<circle cx="560" cy="300" r="10" fill="none" stroke="#cfcac2" stroke-width="5"/>
<path d="M560 300 C460 230 380 330 300 270 C230 220 200 300 160 260" fill="none" stroke="#e9d9bf" stroke-width="4"/>
<rect x="120" y="860" width="220" height="40" rx="10" fill="url(#k)" transform="rotate(-10 230 880)"/>
<rect x="520" y="880" width="200" height="22" rx="10" fill="#9b9690"/>
<circle cx="740" cy="890" r="26" fill="#e9d9bf"/><circle cx="740" cy="890" r="10" fill="#9b8a6e"/>"""
    return frame(bg, body)


def swatches(bg: str) -> str:
    items = []
    for i, c in enumerate(["siyah", "taba", "kahve", "bordo", "yesil", "bej"]):
        x, y = 170 + (i % 2) * 290, 230 + (i // 2) * 250
        items.append(f"<defs>{grad('s' + str(i), c)}</defs>{shadow(x + 125, y + 205, 110, 14)}"
                     f'<path d="M{x} {y + 20} Q{x} {y} {x + 20} {y} L{x + 230} {y + 8} L{x + 250} {y + 190} L{x + 10} {y + 200} Z" fill="url(#s{i})"/>'
                     + stitch(f"M{x + 22} {y + 26} L{x + 226} {y + 32}"))
    return frame(bg, "".join(items))


def giftbox(bg: str) -> str:
    body = f"""{shadow(432, 880, 270, 30)}
<rect x="182" y="470" width="500" height="400" rx="16" fill="#ece4d6"/>
<rect x="160" y="400" width="544" height="110" rx="14" fill="#f6f1e8"/>
<rect x="404" y="400" width="56" height="470" fill="#7a2a2e"/>
<path d="M432 400 C340 300 270 360 330 400 Z M432 400 C524 300 594 360 534 400 Z" fill="#7a2a2e"/>
<rect x="230" y="740" width="130" height="80" rx="6" fill="#fffaf2" transform="rotate(-6 295 780)"/>
<path d="M252 770 L336 762 M254 790 L322 784" stroke="#b9ab96" stroke-width="5" stroke-linecap="round"/>"""
    return frame(bg, body)


PHOTOS = [
    ("siyah-canta.jpg", "Siyah Tote Çanta", "Bitkisel tabaklanmış dana derisi. İç fermuarlı cep var. Laptop sığar (14 inç).", ["canta"], lambda: tote("siyah", "krem")),
    ("taba-canta.jpg", "Taba Tote Çanta", "Kullandıkça rengi koyulaşır ve güzelleşir. Omuz askısı 60 cm.", ["canta"], lambda: tote("taba", "kum")),
    ("bordo-canta.jpg", "Bordo Tote Çanta", "Sınırlı sayıda üretildi. Pirinç kilit.", ["canta"], lambda: tote("bordo", "gul")),
    ("taba-cuzdan.jpg", "Taba Cüzdan", "6 kart bölmesi, bozuk para gözü. El dikişi.", ["cuzdan"], lambda: wallet("taba", "krem")),
    ("siyah-cuzdan.jpg", "Siyah Cüzdan", "İnce yapı, arka cebe rahat sığar.", ["cuzdan"], lambda: wallet("siyah", "gri")),
    ("kahve-kemer.jpg", "Kahve Kemer", "Tek parça deri, pirinç toka. Bel ölçüsüne göre kesilir.", ["kemer"], lambda: belt("kahve", "kum")),
    ("yesil-kartlik.jpg", "Yeşil Kartlık", "4 kart, ortada banknot bölmesi. İsim baskısı yapılabilir.", ["kartlik"], lambda: cardholder("yesil", "yesil")),
    ("bej-kartlik.jpg", "Bej Kartlık", "Hafif ve ince. Kişiye özel harf baskısı.", ["kartlik"], lambda: cardholder("bej", "krem")),
    ("kahve-sirt.jpg", "Kahve Sırt Çantası", "Günlük kullanım için. Dış cep, ayarlanabilir askılar.", ["canta"], lambda: backpack("kahve", "gri")),
    ("anahtarlik.jpg", "Deri Anahtarlık", "Atölyedeki kesimlerden kalan derilerle yapılır, israf olmaz.", ["aksesuar"], lambda: keychain("taba", "yesil")),
    ("atolye.jpg", "Taba Tote Çanta", "Deri tek tek elde kesiliyor. Bir çanta yaklaşık iki gün sürüyor.", ["atolye", "surec"], lambda: workshop("krem")),
    ("deri-secimi.jpg", "Kartlık", "Altı renk seçeneği: siyah, taba, kahve, bordo, yeşil, bej. İsim baskısı ücretsiz.", ["renk"], lambda: swatches("gri")),
    ("paketleme.jpg", "Hediye Paketi", "Her sipariş kutulu ve kurdeleli gönderilir. Not kartı eklenebilir.", ["paket"], lambda: giftbox("gul")),
]

VIDEOS = [
    ("reel-dikis.mp4", "Taba Cüzdan", "Kenar dikişi elde atılıyor. Her ilmek tek tek.", ["atolye", "surec"], "atolye.jpg"),
    ("reel-canta.mp4", "Siyah Tote Çanta", "Yakın plan: doku, kilit ve iç cep.", ["canta"], "siyah-canta.jpg"),
    ("reel-paket.mp4", "Hediye Paketi", "Sipariş paketleniyor: kutu, kurdele, not kartı.", ["paket"], "paketleme.jpg"),
    ("reel-renkler.mp4", "Kartlık", "Altı renk seçeneği. Hangisi sizin?", ["renk"], "deri-secimi.jpg"),
]


def run(*args: str) -> None:
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, title, notes, tags, make in PHOTOS:
            svg = Path(tmp) / (name + ".svg")
            png = Path(tmp) / (name + ".png")
            svg.write_text(make(), encoding="utf-8")
            run("rsvg-convert", "-w", str(W), "-h", str(H), str(svg), "-o", str(png))
            run("ffmpeg", "-y", "-i", str(png), "-q:v", "5", str(OUT / name))
            manifest.append({"file": name, "kind": "image", "title": title, "notes": notes, "tags": tags, "width": W, "height": H})
        for name, title, notes, tags, src in VIDEOS:
            # 9:16 video: the photo slowly zooms in, with a soft vignette. 9 seconds, small file.
            vf = ("split[a][b];[a]scale=1440:2560:force_original_aspect_ratio=increase,crop=1440:2560,boxblur=40:2[bg];"
                  "[b]scale=1440:-2[fg];[bg][fg]overlay=0:(H-h)/2,"
                  "zoompan=z='min(zoom+0.0011,1.18)':d=270:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=30,"
                  "vignette=PI/6,format=yuv420p")
            run("ffmpeg", "-y", "-loop", "1", "-i", str(OUT / src), "-vf", vf, "-t", "9", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "30", "-movflags", "+faststart", "-an", str(OUT / name))
            poster = name.replace(".mp4", ".poster.jpg")
            run("ffmpeg", "-y", "-ss", "1", "-i", str(OUT / name), "-frames:v", "1", "-vf", "scale=360:-2", "-q:v", "5", str(OUT / poster))
            manifest.append({"file": name, "kind": "video", "title": title, "notes": notes, "tags": tags, "width": 720, "height": 1280,
                             "duration": 9.0, "poster": poster})
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(p.stat().st_size for p in OUT.iterdir())
    print(f"{len(manifest)} files, {total / 1024:.0f} KB")


if __name__ == "__main__":
    main()
