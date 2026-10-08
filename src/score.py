#!/usr/bin/env python3
"""Rule-based prioritization. Deterministic, explainable, cheap. No LLM."""
import argparse, json, os, re
from datetime import datetime, timezone

URGENCY_KEYWORDS = re.compile(
    r"\b(urgent|asap|blocker|blocked|deadline|eod|eow|critical|p0|p1|broken|down|incident|sev[12])\b",
    re.I,
)
ESCALATION_KEYWORDS = re.compile(
    r"\b(escalat|follow[- ]?up|still waiting|no response|bump|anyone\?)\b", re.I,
)


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def score_item(item, config, now=None):
    """Score 0-10. Higher = more urgent."""
    now = now or datetime.now(timezone.utc)
    s = config.get("scoring", {})
    total = 0.0
    reasons = []

    # Deadline proximity
    w = s.get("deadline_weight", 0.30)
    if item.get("deadline_hours") is not None:
        dh = item["deadline_hours"]
        if dh <= 24:
            total += w * 10
            reasons.append(f"deadline in {dh}h")
        elif dh <= 72:
            total += w * 7
            reasons.append(f"deadline in {dh}h")
        elif dh <= 168:
            total += w * 4
            reasons.append(f"deadline in {dh}h")
        else:
            total += w * 1

    # Stakeholder weight
    w = s.get("stakeholder_weight", 0.25)
    if item.get("sender_id") in config.get("priority_people", []):
        total += w * 10
        reasons.append("priority sender")

    # Urgency keywords
    w = s.get("urgency_keyword_weight", 0.20)
    hits = URGENCY_KEYWORDS.findall(item.get("text", ""))
    if hits:
        total += w * min(len(hits), 5) * 2
        reasons.append(f"urgency keywords: {hits[:3]}")

    # Escalation signals
    w = s.get("escalation_weight", 0.15)
    if ESCALATION_KEYWORDS.search(item.get("text", "")):
        total += w * 10
        reasons.append("escalation language")

    # Aging boost
    w = s.get("aging_boost_per_4h", 0.05)
    age_h = item.get("age_hours", 0)
    boost = w * (age_h / 4)
    total += min(boost, 2.0)  # cap
    if boost > 0.5:
        reasons.append(f"aging +{boost:.1f}")

    # Channel tier bonus
    tier = item.get("channel_tier", "default")
    if tier == "vip":
        total += 1.5
        reasons.append("VIP channel")
    elif tier == "priority":
        total += 0.75

    confidence = item.get("confidence", 1.0)
    low = confidence < s.get("low_confidence_threshold", 0.6)
    return {
        "score": round(min(total, 10), 2),
        "reasons": reasons,
        "low_confidence": low,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="JSON file of extracted items")
    parser.add_argument("--config", default=".slack-calm/config.json")
    parser.add_argument("--output", default=".slack-calm/scored.json")
    args = parser.parse_args()

    items = load_json(args.input, [])
    config = load_json(args.config, {})
    scored = []
    for item in items:
        result = score_item(item, config)
        item.update(result)
        scored.append(item)
    scored.sort(key=lambda x: -x["score"])
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(scored, f, indent=2)
    print(f"Scored {len(scored)} items -> {args.output}")
    for item in scored[:10]:
        flag = " [LOW CONF]" if item["low_confidence"] else ""
        print(f"  {item['score']:5.2f} {item.get('channel','?'):20s} {item.get('summary','')[:60]}{flag}")


if __name__ == "__main__":
    main()
