import httpx

from tellal.brand import Brand
from tellal.config import Settings
from tellal.content import llm_generate
from tellal.llm import make_chat, parse_json


def test_parse_json_tolerates_fences():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('sure! {"a": 2} ok') == {"a": 2}
    assert parse_json("no") is None


def test_llm_output_is_checked_and_completed():
    def h(req):
        content = '{"caption": "Yeni sezon burada.\\n\\nDetaylar için yazın. #a #b", "hashtags": ["x","y","z","w","v","u","t"]}'
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    chat = make_chat(Settings(llm_enabled=True), transport=httpx.MockTransport(h))
    d = llm_generate(
        Brand(), [{"id": 1, "title": "Çanta", "kind": "image"}], "post", "urun", "tr", None, 1, True, False, chat
    )
    assert d.engine == "llm"
    assert "#a" not in d.caption and "#reklam" in d.caption.split("\n")[0]  # tags out of caption, disclosure up front
    assert len(d.hashtags) <= 4 and d.alt_text  # 5 minus the #reklam tag; alt text filled from the template


def test_llm_down_falls_back():
    def h(req):
        raise httpx.ConnectError("down")

    chat = make_chat(Settings(llm_enabled=True), transport=httpx.MockTransport(h))
    assert chat("s", {}) is None
