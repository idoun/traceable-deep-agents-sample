---
version: "2026-08-02"
---

# Daily News Freshness

Use this skill when a request asks for today's, latest, or current TechNews
items.

Operational rule:

- TechNews stores a GeekNews digest in the morning for the previous day.
- If the user asks for today's news, answer from the latest collected issue and
  explicitly say that today's collection may not be available yet.
- Preserve the latest issue date in the answer whenever the tool result includes
  `issue_date`.
- Do not claim real-time collection unless the tool result proves it.
