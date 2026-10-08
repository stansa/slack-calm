---
name: slack-calm-setup
description: Scan a Slack workspace and propose a tiered priority config for slack-calm. Run once per user before the dashboard skill.
---

# slack-calm setup

## Goal

Produce `.slack-calm/config.json` tailored to this user's actual workspace — not a generic template.

## Steps

1. Run `python src/fetch.py --mode metadata` to pull every channel: name, member count, topic, last-activity timestamp, unread count.
2. Cluster channels into three groups from the data:
   - **High-traffic noise**: many messages, low personal relevance (bot spam, deploy channels, social).
   - **Dead channels**: no messages in 30+ days. Flag separately as archive candidates.
   - **Active and relevant**: recent messages, human senders, topics matching the user's projects.
3. Propose tiers:
   - **VIP**: channels where the user is frequently @mentioned or that contain incidents/escalations. Always deep-read.
   - **Priority**: active project channels. Deep-read when they change.
   - **Default**: everything else. Metadata-only, one-line summaries.
4. Identify priority people: the top senders of messages the user actually replied to.
5. Identify noise filters: bot IDs, recurring automated keywords, channels that are pure FYI.
6. Write the proposal to `.slack-calm/config.proposed.json` and present it to the user for review before writing `config.json`.
7. Never write `config.json` without explicit user approval.

## Output format

Present the proposal as a short summary: channel counts per tier, top five VIP candidates, dead channel list, and suggested priority people. Ask the user to confirm or edit before saving.
