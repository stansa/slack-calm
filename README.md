# slack-calm

A read-only Slack triage system for Claude Code. Instead of drowning in the live firehose, you get a calm, prioritized HTML dashboard you open when you're ready.

## The problem

Slack was supposed to organize work. With hundreds of channels, it became the number one source of disorganization. Anyone can create a channel, so everyone does. DMs pile up. Mentions scatter. Nobody knows what actually needs them.

## The approach

**Read-only by design.** This system never posts, edits, or sends anything in Slack. It only reads. That makes it safe to deploy across a whole team without worrying about an agent going rogue.

**Two-pass token economy.** Pass one is cheap: Python pulls channel metadata, unread counts, and last-message timestamps through the Slack API directly. Pass two is expensive: Claude only deep-reads channels that actually changed since the last run, using a checkpoint file so nothing gets re-processed.

**Scan-first setup.** A setup skill scans your workspace and proposes your tiering from real data — VIP channels, priority channels, dead channels, noise patterns. You review and edit. The dashboard skill then reads that config every run instead of re-deciding from scratch.

**Deterministic scoring.** Prioritization is rule-based (sender role, urgency keywords, deadline proximity, aging). The LLM only handles subjective extraction and summarization. Cheap rules do the scoring; expensive model calls only fire on ambiguous cases.

**Fixed taxonomy.** Reply needed / Review / Noise. No free-text labels. Low-confidence items get flagged, not silently misfiled.

**Aging.** Items that sit unanswered get promoted over time, not buried under newer noise.

## Quick start

1. Clone this repo.
2. Copy `.env.example` to `.env` and add your Slack token (read-only scopes: `channels:read`, `groups:read`, `im:read`, `mpim:read`, `users:read`, `search:read`).
3. Run the setup skill in Claude Code: it scans your channels and proposes a config.
4. Review and edit `.slack-calm/config.json`.
5. Run the dashboard skill to generate `dashboard.html`.
6. Open `dashboard.html` in a browser. That's your calm view.

## Automation: your choice, not ours

This repo ships **no automation**. The dashboard skill is a manual command — you run it when you want a fresh view, and that's the default. Automation is documented here as an option so each person or team can pick the level that fits, without the project imposing one.

- **Manual (default):** run the dashboard skill whenever you want a calm view. Zero background processes, zero surprise token spend.
- **While a session is open:** Claude Code's `/loop 1h rebuild my slack dashboard` regenerates the file hourly during that session. Dies when you close the terminal — which is fine if you like that.
- **Persistent, local:** a plain cron job or systemd timer calling `claude -p` with the dashboard skill's prompt. Survives restarts; you own the schedule.
- **Persistent, cloud:** GitHub Actions on a schedule, or any CI that can run `claude -p`. Useful if you want the dashboard always fresh without a laptop running.

The repo includes none of these — no workflow files, no cron examples, no timers. If you want one, copy the pattern from any of the above; the skill prompt is the same regardless of how it's triggered. The design principle: the expensive part (LLM deep-reads) only fires on the delta since the last checkpoint, so even an hourly loop on a hundred quiet channels costs almost nothing.

## Repo structure

```
README.md
.env.example
.slack-calm/
  config.example.json      # Tiering, priority people, noise filters
  checkpoint.example.json  # Last-seen timestamps per channel
skills/
  setup/SKILL.md           # Scan workspace, propose tiering
  dashboard/SKILL.md       # Build the HTML dashboard
src/
  fetch.py                 # Deterministic Slack API fetcher (metadata + delta)
  score.py                 # Rule-based prioritization
  render.py                # HTML dashboard generator
```

## Design principles (stolen shamelessly from others, then adapted)

- **Context files beat prompts** — the Akshat2430 ai-chief-of-staff repo showed the same triage prompt producing generic output without context files. Ours ships a config the setup skill generates from your real data.
- **Fixed taxonomy** — Kipwise and the Slack Workflow Builder projects both warn that free-text labels break routing. We use three tiers with confidence thresholds.
- **Deterministic scoring** — Chief-of-Staff-AI keeps prioritization rule-based and explainable while the LLM does extraction. Same split here.
- **Read-first, write-cautious** — mboverell's ai-chief-of-staff principle: all memory lives in plain text files you own.
- **Pull only what changed** — Yash Tekriwal's Clay system filtered to notification-generating messages and compared against stored read state. Our checkpoint file does the same.
- **Tiered processing** — Slack's own engineering team batch-processes recaps overnight and rate-limits real-time calls because inference on every message is too expensive even for them.

## Differentiators

1. **Setup skill as a product** — scan-first onboarding that proposes tiering from real data, not manual configuration.
2. **Team template** — one shared skill, per-person config. Deploy across a team without per-user token burn.
3. **Visible uncertainty** — low-confidence classifications are flagged, not guessed.
4. **Aging** — stale items get promoted, not buried.
5. **No imposed automation** — the project stays a tool you run, not a daemon that runs you.

## Token budget

Designed so a hundred channels with nothing new costs almost nothing. The expensive LLM pass only fires on the delta, batched ten channels per call, with cached system prompts.

## License

MIT
