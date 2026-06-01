"""
pricing.py — turn token usage into dollars.

Cost is a first-class axis in FireDrill, NOT folded into the quality composite.
To compare it fairly across model tiers we price the four billable token buckets
(uncached input, output, cache read, cache write) per model and sum to a dollar
figure. Rates are USD per 1M tokens.

These rates are APPROXIMATE and configurable — update them to the current public
prices (or override PRICING) before quoting absolute dollars. gpt-5.5 in
particular is a placeholder until its real pricing is set.
"""

from __future__ import annotations

# USD per 1,000,000 tokens. Keys are FireDrill registry model names.
# cache_write defaults to 1.25× input, cache_read to 0.1× input where a provider
# offers prompt caching.
PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-8":  {"input": 15.0, "output": 75.0, "cache_read": 1.50, "cache_write": 18.75},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00, "cache_read": 0.10, "cache_write": 1.25},
    "gpt-5.5":          {"input": 10.0, "output": 30.0, "cache_read": 2.50, "cache_write": 10.0},
    "gpt-4.1-mini":     {"input": 0.40, "output": 1.60, "cache_read": 0.10, "cache_write": 0.40},
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
