#!/usr/bin/env python3
"""Render scored items into a self-contained dashboard.html. No LLM."""
import argparse, html, json, os
from datetime import datetime, timezone


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def esc(s):
    return html.escape(str(s or ""))


def render(items, config):
    style = (config.get("dashboard") or {}).get("style", "clean")
    max_per_tier = (config.get("dashboard") or {}).get("max_items_per_tier", 15)

    tiers = {"reply_needed": [], "review": [], "noise": []}
    for item in items:
        tier = item.get("tier", "review")
        if tier not in tiers:
            tier = "review"
        tiers[tier].append(item)

    sections_html = []
    labels = {
        "reply_needed": ("Reply Needed", "#c0392b"),
        "review": ("Review", "#d68910"),
        "noise": ("Noise", "#7f8c8d"),
    }
    for key, (label, color) in labels.items():
        group = tiers[key][:max_per_tier]
        if key == "noise" and (config.get("dashboard") or {}).get("show_noise_as_counts"):
            # summarize noise as counts by channel
            from collections import Counter
            counts = Counter(i.get("channel", "?") for i in tiers["noise"])
            body = "".join(
                f"<li>{esc(ch)}: {n}</li>" for ch, n in counts.most_common(10)
            ) or "<li>None</li>"
            sections_html.append(
                f"<section><h2 style='color:{color}'>{label} ({len(tiers['noise'])})</h2><ul>{body}</ul></section>"
            )
            continue
        cards = []
        for item in group:
            conf = ""
            if item.get("low_confidence"):
                conf = " <span class='flag'>low confidence</span>"
            cards.append(
                f"""<article class='card'>
  <header>
    <strong>{esc(item.get('sender', '?'))}</strong> in #{esc(item.get('channel', '?'))}
    <time>{esc(item.get('timestamp', ''))}</time>{conf}
  </header>
  <p class='summary'>{esc(item.get('summary', ''))}</p>
  <p class='why'><em>Why it matters:</em> {esc(item.get('why', ''))}</p>
  <p class='next'><em>Next step:</em> {esc(item.get('next_step', ''))}</p>
  {f"<a href='{esc(item.get('permalink'))}'>open in Slack</a>" if item.get('permalink') else ''}
  <p class='score'>score {item.get('score', 0)} — {esc(', '.join(item.get('reasons', [])[:3]))}</p>
</article>"""
            )
        sections_html.append(
            f"<section><h2 style='color:{color}'>{label} ({len(tiers[key])})</h2>{''.join(cards) or '<p>All clear.</p>'}</section>"
        )

    # synthesis note
    synth = ""
    if items:
        top = items[0]
        synth = (
            f"<aside class='synth'><strong>Note:</strong> Top item is "
            f"{esc(top.get('summary', ''))} from #{esc(top.get('channel', ''))}. "
            f"Protect your first 90 minutes for it.</aside>"
        )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!DOCTYPE html>
<html lang='en'><head><meta charset='utf-8'><title>slack-calm — {now}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #2c3e50; background: #f7f9fb;}}
  h1 {{ font-size: 1.4rem;}}
  h2 {{ border-bottom: 2px solid #ecf0f1; padding-bottom: .3rem;}}
  .card {{ background: #fff; border: 1px solid #e1e8ed; border-radius: 8px; padding: 1rem; margin: .8rem 0;}}
  .card header {{ display: flex; justify-content: space-between; font-size: .85rem; color: #7f8c8d;}}
  .flag {{ background: #fdebd0; color: #9a7d0a; border-radius: 4px; padding: 0 .4rem; font-size: .75rem;}}
  .synth {{ background: #eaf2f8; border-left: 4px solid #2980b9; padding: .8rem 1rem; margin: 1rem 0;}}
  a {{ color: #2980b9;}}
</style></head><body>
<h1>slack-calm <small style='color:#7f8c8d;font-weight:normal'>{now}</small></h1>
{synth}
{''.join(sections_html)}
</body></html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=".slack-calm/scored.json")
    parser.add_argument("--config", default=".slack-calm/config.json")
    parser.add_argument("--output", default="dashboard.html")
    args = parser.parse_args()

    items = load_json(args.input, [])
    config = load_json(args.config, {})
    page = render(items, config)
    with open(args.output, "w") as f:
        f.write(page)
    print(f"Rendered {len(items)} items -> {args.output}")


if __name__ == "__main__":
    main()
