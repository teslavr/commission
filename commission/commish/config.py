"""Configuration.

One question decides everything: which model do you write code with?
That model becomes the MASTER -- it speaks to you, in one voice.
The COMMITTEE is then assembled from top models of *other* vendors, because a
model cannot see its own blind spots.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

# One strong model per vendor, all reachable through a single Bedrock credential.
# Run `commish models` to see what your account can actually call -- Bedrock
# model access is off by default and IDs move between regions.
CATALOG = {
    # Verified live against a real Bedrock account, 2026-08-18.
    # Model access is per-account and geo-restricted (Llama 4 is unavailable in
    # the EU, for one), so `commish models` is not a nicety -- it is how you find
    # out what your account can actually call before the committee fails at 3am.
    "anthropic": "us.anthropic.claude-opus-4-6-v1",
    "meta": "us.meta.llama3-3-70b-instruct-v1:0",
    "mistral": "us.mistral.pixtral-large-2502-v1:0",
    "deepseek": "us.deepseek.r1-v1:0",
    "writer": "us.writer.palmyra-x5-v1:0",
    "amazon": "us.amazon.nova-pro-v1:0",
}

# USD per 1M tokens, (input, output). INDICATIVE ONLY -- Bedrock pricing varies by
# region and changes without warning. Override in .commish.yml with the rates on your
# own invoice; `commish stats` reports what it used so the arithmetic stays checkable.
PRICES = {
    "us.anthropic.claude-opus-4-6-v1": (5.00, 25.00),
    "us.anthropic.claude-sonnet-4-6": (3.00, 15.00),
    "us.anthropic.claude-haiku-4-5-20251001-v1:0": (1.00, 5.00),
    "us.meta.llama3-3-70b-instruct-v1:0": (0.72, 0.72),
    "us.mistral.pixtral-large-2502-v1:0": (2.00, 6.00),
    "us.deepseek.r1-v1:0": (1.35, 5.40),
    "us.writer.palmyra-x5-v1:0": (0.60, 6.00),
    "us.amazon.nova-pro-v1:0": (0.80, 3.20),
}


def price_of(model_id: str, prices: dict | None = None) -> tuple[float, float] | None:
    table = prices or PRICES
    return table.get(model_id)


DEFAULT_MASTER = CATALOG["anthropic"]
COMMITTEE_SIZE = 3


def vendor_of(model_id: str) -> str:
    """`us.anthropic.claude-opus-5` -> `anthropic`."""
    parts = model_id.split(".")
    for part in parts:
        if part in CATALOG:
            return part
    return parts[1] if len(parts) > 1 else parts[0]


def default_committee(master: str, size: int = COMMITTEE_SIZE) -> list[str]:
    """Every vendor except the master's own."""
    mine = vendor_of(master)
    return [model for vendor, model in CATALOG.items() if vendor != mine][:size]


@dataclass
class Config:
    region: str = "us-east-1"
    # The model you write code with. Reviews the committee, writes the comment.
    master: str = DEFAULT_MASTER
    # Left empty -> assembled from CATALOG, excluding the master's vendor.
    committee: list[str] = field(default_factory=list)
    # How many committee members must raise an issue before the master is
    # forbidden from suppressing it.
    consensus_floor: int = 2
    min_severity: str = "low"
    verify_command: str | None = None
    max_tokens: int = 8000
    prices: dict = field(default_factory=lambda: dict(PRICES))
    tone: str = (
        "Voice: a Sicilian-American wiseguy of the old school. Dry, theatrical, "
        "faintly weary. Speak in the idiom — business, respect, the table, the books — "
        "but never threaten anyone and never break technical precision for a joke. "
        "The most cutting thing you can say about bad code is that it is disrespectful."
    )

    def __post_init__(self) -> None:
        if not self.committee:
            self.committee = default_committee(self.master)

    @classmethod
    def load(cls, path: str | None = None) -> "Config":
        data: dict = {}
        candidate = Path(path) if path else Path(".commish.yml")
        if candidate.exists():
            if yaml is None:
                raise RuntimeError("PyYAML is required to read .commish.yml")
            data = yaml.safe_load(candidate.read_text()) or {}

        cfg = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        cfg.region = (
            os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or cfg.region
        )
        return cfg


SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}


def severity_at_least(value: str, floor: str) -> bool:
    return SEVERITY_ORDER.get(value, 0) >= SEVERITY_ORDER.get(floor, 0)
