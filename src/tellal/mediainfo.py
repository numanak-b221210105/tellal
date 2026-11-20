"""Reads image size from JPEG/PNG/WebP headers and video length from MP4/MOV, without extra libraries."""

from __future__ import annotations

import struct


def image_size(data: bytes) -> tuple[int, int] | None:
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        chunk = data[12:16]
        if chunk == b"VP8X":
            w = int.from_bytes(data[24:27], "little") + 1
            h = int.from_bytes(data[27:30], "little") + 1
            return w, h
        if chunk == b"VP8 ":
            w, h = struct.unpack("<HH", data[26:30])
            return w & 0x3FFF, h & 0x3FFF
        if chunk == b"VP8L":
            b = int.from_bytes(data[21:25], "little")
            return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            seg = struct.unpack(">H", data[i + 2 : i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5 : i + 9])
                return w, h
            i += 2 + seg
    return None


def _boxes(data: bytes, start: int, end: int):  # noqa: ANN202
    i = start
    while i + 8 <= end:
        size, kind = struct.unpack(">I4s", data[i : i + 8])
        header = 8
        if size == 1 and i + 16 <= end:
            size = struct.unpack(">Q", data[i + 8 : i + 16])[0]
            header = 16
        elif size == 0:
            size = end - i
        if size < header:
            return
        yield kind, i + header, i + size
        i += size


def video_info(data: bytes) -> dict[str, float]:
    """Duration (s) and the first video track's display size from an MP4/MOV 'moov' box."""
    out: dict[str, float] = {}
    for kind, s, e in _boxes(data, 0, len(data)):
        if kind != b"moov":
            continue
        for k2, s2, e2 in _boxes(data, s, e):
            if k2 == b"mvhd":
                v = data[s2]
                if v == 1:
                    scale, dur = struct.unpack(">IQ", data[s2 + 20 : s2 + 32])
                else:
                    scale, dur = struct.unpack(">II", data[s2 + 12 : s2 + 20])
                if scale:
                    out["duration"] = dur / scale
            if k2 == b"trak" and "width" not in out:
                for k3, _s3, e3 in _boxes(data, s2, e2):
                    if k3 == b"tkhd":
                        w, h = struct.unpack(">II", data[e3 - 8 : e3])
                        if w and h:
                            out["width"], out["height"] = w / 65536, h / 65536
    return out
