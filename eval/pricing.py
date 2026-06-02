"""
pricing.py — turn token usage into dollars.

Cost is a first-class axis in FireDrill, NOT folded into the quality composite.
To compare it fairly across model tiers we price the four billable token buckets
(uncached input, output, cache read, cache write) per model and sum to a dollar
figure. Rates are USD per 1M tokens.

Rates below are the published per-1M-token API prices for each model, sourced
from the providers' pricing pages (fetched 2026-06; see per-row citations). If
prices change, update them here or override PRICING.
"""

from __future__ import annotations

# USD per 1,000,000 tokens. Keys are FireDrill registry model names.
# Anthropic charges cache writes separately (5-min: 1.25× input); OpenAI does
# not bill cache writes, so cache_write is 0 for OpenAI (and our OpenAI usage
# never reports cache-creation tokens anyway). cache_read is the cached/hit rate.
PRICING: dict[str, dict[str, float]] = {
    # Anthropic — https://platform.claude.com/docs/en/about-claude/pricing
    "claude-opus-4-8":  {"input": 5.00, "output": 25.0, "cache_read": 0.50, "cache_write": 6.25},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00, "cache_read": 0.10, "cache_write": 1.25},
    # OpenAI — https://developers.openai.com/api/docs/pricing (gpt-5.5) and
    #          https://developers.openai.com/api/docs/models/gpt-4.1-mini
    "gpt-5.5":          {"input": 5.00, "output": 30.0, "cache_read": 0.50, "cache_write": 0.0},
    "gpt-4.1-mini":     {"input": 0.40, "output": 1.60, "cache_read": 0.10, "cache_write": 0.0},
}

# Models we don't have a price for are scored with cost 0 and flagged, rather
# than crashing a run.
_UNKNOWN = {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0}


def cost_usd(model: str, usage: dict[str, int]) -> float:
    """Dollar cost of one episode's token usage. usage keys: input_tokens,
    output_tokens, cache_read_tokens, cache_write_tokens."""
    rates = PRICING.get(model, _UNKNOWN)
    dollars = (
        usage.get("input_tokens", 0) * rates["input"]
        + usage.get("output_tokens", 0) * rates["output"]
        + usage.get("cache_read_tokens", 0) * rates["cache_read"]
        + usage.get("cache_write_tokens", 0) * rates["cache_write"]
    ) / 1_000_000
    return round(dollars, 6)


def has_pricing(model: str) -> bool:
    return model in PRICING
