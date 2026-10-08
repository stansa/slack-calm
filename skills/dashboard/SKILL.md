---
name: slack-calm-dashboard
description: Build a calm, prioritized HTML dashboard from Slack. Reads .slack-calm/config.json and generates dashboard.html. Read-only — never posts to Slack.
---

# slack-calm dashboard

## Goal

Generate one self-contained `dashboard.html` the user opens in a browser. No Slack writes. No live firehose.

## Steps

1. Load `.slack-calm/config.json` and `.slack-calm/checkpoint.json`.
2. Run `python src/fetch.py --mode delta` to pull only messages newer than each channel's checkpoint. This is the cheap pass.
3. Filter out noise using config noise filters (bots, keywords) before any LLM call.
4. Batch remaining changed channels into groups of ten. For each batch, one LLM call extracts: one-line summary, taxonomy tier (reply needed / review / noise), confidence score, and any action items with owners.
5. Run `python src/score.py` to apply deterministic prioritization: deadline proximity, stakeholder weight, urgency keywords, escalation signals, aging boost. Low-confidence items below the threshold get flagged, not ranked.
6. Run `python src/render.py` to emit `dashboard.html`: three sections (Reply Needed, Review, Noise-as-counts), each item with sender, channel, timestamp, one-line summary, why it matters, recommended next step, and a permalink. Aging items promoted to the top. A short synthesis note across items (pattern the human might miss).
7. Update `.slack-calm/checkpoint.json` with new last-seen timestamps — only after a successful render.
8. If the run produced no changes, say so and exit. Do not regenerate.

## Scheduling

- Interactive: run the skill whenever you want a fresh view.
- Hourly while a session is open: `/loop 1h rebuild my slack dashboard`.
- Persistent: cron or GitHub Actions calling `claude -p` with this skill's prompt.

## Hard rules

- Never post, edit, or react in Slack.
- Never send email or messages on the user's behalf.
- Never guess an owner when two people could own an ask — flag it instead.
- Cache the system prompt and config across runs to avoid re-sending identical instructions.
