---
version: "2026-08-02"
---

# Tech Trend Briefing

Use this skill when a request asks for comparison, trend analysis, risk,
strategy, priority, investment perspective, or report-style synthesis.

Workflow:

- Start with a bounded search over the user's topic.
- Prefer evidence from multiple items when available.
- Expand to article detail before making strong claims.
- Separate observation, interpretation, and limitation.
- Keep source titles, slugs, and issue dates available for the final answer.

Current runtime note:

- The deterministic light path can only execute one read-only TechNews tool
  call, so deep candidates should be traced as requiring this skill even when
  they temporarily fall back to the light path.
