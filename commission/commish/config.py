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

PROVIDERS = ("bedrock", "openrouter")

# One strong model per vendor, all reachable through a single credential.
# Run `commish models` to see what your account can actually call -- Bedrock
# model access is off by default and IDs move between regions.
BEDROCK_CATALOG = {
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

# The same idea through OpenRouter: one key, and the vendors Bedrock does not
# carry (OpenAI, Google, xAI) come with it. Order is the order the committee is
# drawn in. Verified against openrouter.ai/api/v1/models, 2026-11-11.
OPENROUTER_CATALOG = {
    "anthropic": "anthropic/claude-opus-5.5",
    "openai": "openai/gpt-6.1-sol",
    "google": "google/gemini-4-argon",
    "deepseek": "deepseek/deepseek-v4-pro-0813",
    "xai": "x-ai/grok-4.7",
    "mistral": "mistralai/mistral-large-4-0",
    "qwen": "qwen/qwen3.8-max-0902",
    "moonshot": "moonshotai/kimi-k3.1-pro",
    "meta": "meta-llama/llama-4-maverick",
}

CATALOGS = {"bedrock": BEDROCK_CATALOG, "openrouter": OPENROUTER_CATALOG}
CATALOG = BEDROCK_CATALOG  # kept for anything that still imports the old name

# OpenRouter's vendor prefixes, where they differ from the vendor's name.
_OPENROUTER_VENDORS = {"meta-llama": "meta", "mistralai": "mistral", "x-ai": "xai",
                       "moonshotai": "moonshot", "z-ai": "zhipu"}

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
    # OpenRouter list prices, 2026-11-11. OpenRouter passes vendor prices through.
    "anthropic/claude-opus-5.5": (4.00, 20.00),
    "anthropic/claude-sonnet-5.5": (2.00, 10.00),
    "openai/gpt-6.1-sol": (2.00, 10.00),
    "google/gemini-4-argon": (2.00, 10.00),
    "deepseek/deepseek-v4-pro-0813": (0.11, 4.44),
    "x-ai/grok-4.7": (2.00, 6.00),
    "mistralai/mistral-large-4-0": (0.70, 2.10),
    "qwen/qwen3.8-max-0902": (2.00, 6.00),
    "moonshotai/kimi-k3.1-pro": (2.00, 10.00),
    "meta-llama/llama-4-maverick": (0.35, 1.00),
}


def price_of(model_id: str, prices: dict | None = None) -> tuple[float, float] | None:
    table = prices or PRICES
    return table.get(model_id)


DEFAULT_MASTER = BEDROCK_CATALOG["anthropic"]
COMMITTEE_SIZE = 3


def provider_of(model_id: str) -> str:
    """OpenRouter ids are `vendor/model`; Bedrock ids never contain a slash."""
    return "openrouter" if "/" in model_id else "bedrock"


def vendor_of(model_id: str) -> str:
    """`us.anthropic.claude-opus-5` -> `anthropic`; `x-ai/grok-4.7` -> `xai`."""
    if "/" in model_id:
        prefix = model_id.split("/", 1)[0]
        return _OPENROUTER_VENDORS.get(prefix, prefix)
    parts = model_id.split(".")
    for part in parts:
        if part in BEDROCK_CATALOG:
            return part
    return parts[1] if len(parts) > 1 else parts[0]


def for_provider(model_id: str, provider: str) -> str:
    """The same vendor's flagship on the other provider.

    A .commish.yml written for Bedrock should still mean something when the
    OpenRouter key is the one in hand: `us.anthropic.claude-opus-4-6-v1` means
    "I write code with Claude", and that survives the switch. A vendor the other
    provider does not carry is kept as written, and fails loudly in `doctor`.
    """
    if provider_of(model_id) == provider:
        return model_id
    return CATALOGS[provider].get(vendor_of(model_id), model_id)


def default_committee(master: str, size: int = COMMITTEE_SIZE, provider: str | None = None) -> list[str]:
    """Every vendor except the master's own."""
    mine = vendor_of(master)
    catalog = CATALOGS[provider or provider_of(master)]
    return [model for vendor, model in catalog.items() if vendor != mine][:size]


def detect_provider() -> str:
    """`auto`: Bedrock if AWS credentials are around, else OpenRouter if its key
    is, else Bedrock -- so the no-credentials message still names both."""
    env = os.environ
    if env.get("AWS_BEARER_TOKEN_BEDROCK") or env.get("AWS_ACCESS_KEY_ID") or env.get("AWS_PROFILE"):
        return "bedrock"
    if env.get("OPENROUTER_API_KEY"):
        return "openrouter"
    return "bedrock"


@dataclass
class Config:
    # bedrock | openrouter | auto. COMMISH_PROVIDER and --provider override it.
    provider: str = "auto"
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
        self._auto_committee = not self.committee
        self.finalize()

    def finalize(self) -> "Config":
        """Settle the provider, then make every model id one it can serve.

        Call again after changing provider, master or committee.
        """
        if self.provider not in PROVIDERS:
            if self.provider not in ("auto", "", None):
                raise ValueError(f"provider must be one of {', '.join(PROVIDERS)} or auto, "
                                 f"not {self.provider!r}")
            self.provider = detect_provider()
        self.master = for_provider(self.master, self.provider)
        if self._auto_committee or not self.committee:
            self._auto_committee = True
            self.committee = default_committee(self.master, provider=self.provider)
        else:
            self.committee = [for_provider(m, self.provider) for m in self.committee]
        return self

    @property
    def where(self) -> str:
        """For status lines: `bedrock us-east-1` or `openrouter`."""
        return f"bedrock {self.region}" if self.provider == "bedrock" else self.provider

    @classmethod
    def load(cls, path: str | None = None) -> "Config":
        data: dict = {}
        candidate = Path(path) if path else Path(".commish.yml")
        if candidate.exists():
            if yaml is None:
                raise RuntimeError("PyYAML is required to read .commish.yml")
            data = yaml.safe_load(candidate.read_text()) or {}

        from .preflight import load_env_file  # so `auto` sees keys kept in ~/.commish.env

        load_env_file()
        fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        if os.environ.get("COMMISH_PROVIDER"):
            fields["provider"] = os.environ["COMMISH_PROVIDER"].strip().lower()
        cfg = cls(**fields)
        cfg.region = (
            os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or cfg.region
        )
        return cfg


SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}


def severity_at_least(value: str, floor: str) -> bool:
    return SEVERITY_ORDER.get(value, 0) >= SEVERITY_ORDER.get(floor, 0)
