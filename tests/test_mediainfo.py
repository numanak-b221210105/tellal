import json
from importlib import resources
from pathlib import Path

from tellal.mediainfo import image_size, video_info

DEMO = Path(str(resources.files("tellal") / "demo_media"))


def test_reads_demo_media():
    for m in json.loads((DEMO / "manifest.json").read_text(encoding="utf-8")):
        data = (DEMO / m["file"]).read_bytes()
        if m["kind"] == "image":
            assert image_size(data) == (m["width"], m["height"])
        else:
            vi = video_info(data)
            assert round(vi["duration"]) == round(m["duration"])
            assert (vi["width"], vi["height"]) == (m["width"], m["height"])


def test_png_header():
    png = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + (640).to_bytes(4, "big") + (480).to_bytes(4, "big")
    assert image_size(png) == (640, 480)
    assert image_size(b"not an image") is None
