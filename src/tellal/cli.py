"""Command line: run the server, or run single steps (useful from cron)."""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tellal", description="Tellal: social media assistant for small businesses.")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("serve", help="start the web panel and the scheduler (default)")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8300)
    sub.add_parser("tick", help="publish due posts and refresh insights/comments once")
    p = sub.add_parser("plan", help="plan the next 7 days (items wait for approval)")
    p.add_argument("--start", help="YYYY-MM-DD, local date of the first day (default: tomorrow)")
    sub.add_parser("check", help="show the connected account and today's publishing quota")
    args = ap.parse_args(argv)

    if args.cmd in (None, "serve"):
        from .serve import main as serve

        return serve(["--host", getattr(args, "host", "127.0.0.1"), "--port", str(getattr(args, "port", 8300))])

    from .api import create_app
    from .brand import load_brand
    from .config import Settings

    settings = Settings()
    app = create_app(settings)
    store, provider = app.state.store, app.state.provider
    if args.cmd == "tick":
        print(json.dumps(app.state.tick(True), ensure_ascii=False))
        return 0
    if args.cmd == "plan":
        from datetime import datetime

        from .clock import tz
        from .llm import make_chat
        from .planner import plan_week

        start = datetime.fromisoformat(args.start).replace(tzinfo=tz(settings.timezone)) if args.start else None
        r = plan_week(store, load_brand(store), settings.timezone, start, make_chat(settings))
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    if args.cmd == "check":
        accs = store.accounts()
        if not accs:
            print("No connected account.")
            return 1
        for a in accs:
            prof = provider.profile(a)
            q = provider.quota(a)
            print(
                f"@{prof['username']} ({prof.get('account_type', a['provider'])}), {prof['followers']} followers, "
                f"published in the last 24 h: {q['used']}/{q['limit']}"
            )
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
