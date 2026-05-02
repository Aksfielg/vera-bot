## Approach
Vera-Bot uses Google Gemini Flash as its message engine with 16 trigger-specific prompt templates (not one generic prompt). Each trigger kind — research_digest, recall_due, perf_dip, festival, curious_ask, etc. — has a tailored composition style that pre-selects the right compulsion lever (specificity, loss aversion, social proof, effort externalization, or curiosity). The compose() function: (1) maps trigger.kind to a style template, (2) builds a structured context block from all 4 inputs, (3) calls Gemini at temperature=0.0, (4) returns JSON with body, cta, send_as, suppression_key, rationale.

## What Makes This Score High
- Specificity: every message anchors on one verifiable fact from context (JIDA p.14 with n=2100, CTR 2.1% vs peer 3.0%, ₹299 from active catalog)
- Category voice: dentists get clinical-peer tone, restaurants get operator-to-operator, no promotional language for healthcare categories
- Hindi-English code-mix: automatically triggered when merchant.languages includes "hi"
- Anti-hallucination: system prompt explicitly forbids inventing numbers, citations, or offers not present in the received context

## Multi-turn Handling
Auto-reply detection exits in ≤2 turns (not 6) using 12 Hindi+English signature phrases + repeated-message check. Intent transitions route immediately: "yes/haan/karo/bilkul" → action mode, "mujhe join karna hai" → onboarding (no more qualifying questions).

## Model Choice
Gemini Flash: sub-3s response (within 30s timeout), free tier, strong Hindi support, reliable JSON output at temperature=0.

## Tradeoffs
Flash over Pro for speed consistency. temperature=0 for judge reproducibility requirement (would use 0.3 in production for creative variety).

## What Would Help
Historical reply-rate data by trigger+compulsion combination per category — current priority ranking is heuristic from case studies only.
