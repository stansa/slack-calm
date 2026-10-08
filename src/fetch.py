#!/usr/bin/env python3
"""Deterministic Slack API fetcher. Metadata pass and delta pass. No LLM."""
import argparse, json, os, time
from datetime import datetime, timezone, timedelta

try:
    from slack_sdk import WebClient
except ImportError:
    print("Install slack-sdk: pip install slack-sdk")
    raise SystemExit(1)

TOKEN = os.environ.get("SLACK_TOKEN")
if not TOKEN:
    print("SLACK_TOKEN not set. Copy .env.example to .env and fill it in.")
    raise SystemExit(1)

client = WebClient(token=TOKEN)


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def metadata_pass():
    """Cheap pass: channel names, member counts, topics, last activity, unreads."""
    channels = []
    cursor = None
    while True:
        resp = client.conversations_list(
            types="public_channel,private_channel,mpim,im",
            exclude_archived=True,
            limit=200,
            cursor=cursor,
        )
        for ch in resp["channels"]:
            channels.append({
                "id": ch["id"],
                "name": ch.get("name") or ch.get("user") or ch["id"],
                "is_im": ch["is_im"],
                "is_mpim": ch["is_mpim"],
                "num_members": ch.get("num_members"),
                "topic": (ch.get("topic") or {}).get("value", ""),
                "unread_count": ch.get("unread_count", 0),
                "last_activity": ch.get("updated"),
            })
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    return channels


def delta_pass(checkpoint, lookback_hours=24, max_deep=10):
    """Expensive pass: only messages newer than each channel's checkpoint."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    cutoff_ts = cutoff.timestamp()
    changed = []
    for ch in metadata_pass():
        cid = ch["id"]
        last_seen = checkpoint.get("channels", {}).get(cid)
        if last_seen and float(last_seen) >= ch.get("last_activity", 0):
            continue  # nothing new
        if ch.get("last_activity", 0) < cutoff_ts and not ch["is_im"]:
            continue  # too old, metadata-only
        changed.append(ch)
    # VIP channels always included
    config = load_json(".slack-calm/config.json", {})
    vip = set(config.get("vip_channels", []))
    changed.sort(key=lambda c: (0 if f"#{c['name']}" in vip else 1, -(c.get("unread_count") or 0)))
    return changed[:max_deep]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["metadata", "delta"], required=True)
    parser.add_argument("--lookback-hours", type=int, default=24)
    parser.add_argument("--max-deep", type=int, default=10)
    args = parser.parse_args()

    checkpoint = load_json(".slack-calm/checkpoint.json", {"channels": {}})

    if args.mode == "metadata":
        data = metadata_pass()
        print(json.dumps(data, indent=2))
    else:
        data = delta_pass(checkpoint, args.lookback_hours, args.max_deep)
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
