"""What we measure, and what we refuse to measure.

The strategy doc names a north-star metric and kill criteria. A product that
cannot compute them is guessing, so every review writes one event.

**Nothing here touches content.** Not the code, not the file path, not the repo
name, not the text of a finding, not a model's raw output. A tool whose pitch is
"your code never leaves your account" does not get to make an exception for its
own analytics. What we keep is shape: which reviewers ran, who agreed, what it
cost, and whether the fix survived verification.

The prototype writes to a local JSONL file and makes no network calls at all.
The hosted version would ship the same records to a collector -- the schema is
already safe to transmit, which is the point of designing it this way first.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("GRUMPY_HOME", Path.home() / ".grumpy"))
EVENTS = HOME / "events.jsonl"
INSTALL = HOME / "install_id"

# One switch, honoured everywhere.
DISABLED = os.environ.get("GRUMPY_NO_TELEMETRY", "").lower() in {"1", "true", "yes"}


def install_id() -> str:
    """A random per-machine id. Not derived from anything about the user."""
    try:
        HOME.mkdir(parents=True, exist_ok=True)
        if INSTALL.exists():
            return INSTALL.read_text().strip()
        new = uuid.uuid4().hex
        INSTALL.write_text(new)
        INSTALL.chmod(0o600)
        return new
    except OSError:
        return "unknown"


def classify_error(message: str) -> str:
    """Errors can quote a model's raw output, which can quote the user's code.
    So we store a category, never the message."""
    lowered = message.lower()
    for needle, label in (
        ("could not parse json", "bad_output_shape"),
        ("accessdenied", "no_model_access"),
        ("throttl", "throttled"),
        ("timeout", "timeout"),
        ("validationexception", "invalid_request"),
        ("credential", "no_credentials"),
    ):
        if needle in lowered:
            return label
    return "other"


def _cost(usage: dict | None, prices: dict | None) -> float:
    return round(
        sum(
            (i * p_in + o * p_out) / 1_000_000
            for m, (i, o) in (usage or {}).items()
            if (rate := (prices or {}).get(m))
            for p_in, p_out in [rate]
        ),
        6,
    )


def _write(event: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    with EVENTS.open("a") as handle:
        handle.write(json.dumps(event) + "\n")


def record_committee(
    *,
    filename: str,
    loc: int,
    surface: str,
    elapsed_ms: int,
    reviewers: list[str],
    live_count: int,
    errors: dict,
    findings_by_model: dict,
    severity: dict,
    fix_offered: bool,
    usage: dict | None = None,
    prices: dict | None = None,
) -> None:
    """One line per review on the committee-only path.

    The caller consolidates on this path, so nothing here knows how many
    findings survived grouping, whether the lead dissented, or whether a fix
    verified -- those fields stay empty rather than guessing. `consolidated_by`
    says `caller` so the two paths never get silently averaged together.
    """
    if DISABLED:
        return
    try:
        _write(
            {
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "install_id": install_id(),
                "surface": surface,
                "file_ext": Path(filename).suffix or "none",
                "loc": loc,
                # No lead ran: the agent on the other end of the call is it.
                "lead_model": None,
                "reviewers": list(reviewers),
                "reviewers_ok": live_count,
                "reviewers_failed": {
                    model: classify_error(err) for model, err in errors.items()
                },
                "findings_raw": sum(findings_by_model.values()),
                # Grouping happens in the caller, so nothing is "published" here.
                "issues_published": 0,
                "unanimous": 0,
                "corroborated": 0,
                "contested": 0,
                "suppressed_by_lead": 0,
                "severity": {
                    level: severity.get(level, 0) for level in ("high", "medium", "low")
                },
                "raised_by": dict(findings_by_model),
                "consolidated_by": "caller",
                "fix_offered": fix_offered,
                # Verification runs with consolidation, which did not happen here.
                "fix_status": "unverified" if fix_offered else "none",
                "elapsed_ms": elapsed_ms,
                "tokens": {m: {"in": i, "out": o} for m, (i, o) in (usage or {}).items()},
                "cost_usd": _cost(usage, prices),
            }
        )
    except Exception:
        pass  # a broken counter must never cost the user a review


def record(
    result,
    *,
    surface: str,
    elapsed_ms: int,
    lead_model: str,
    reviewers: list[str],
    usage: dict | None = None,
    prices: dict | None = None,
) -> None:
    """One line per review. Never raises -- analytics must not break a review."""
    if DISABLED:
        return
    try:
        issues = result.issues
        event = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "install_id": install_id(),
            "surface": surface,
            # Shape of the input, not the input.
            "file_ext": Path(result.filename).suffix or "none",
            "loc": result.original.count("\n") + 1,
            # Which reviewers ran, and which failed.
            "lead_model": lead_model,
            "reviewers": list(reviewers),
            "reviewers_ok": result.review.committee_size,
            "reviewers_failed": {
                model: classify_error(err) for model, err in result.committee_errors.items()
            },
            # Did agreement actually happen? This is the assumption under the product.
            "findings_raw": sum(len(i.findings) for i in result.review.issues),
            "issues_published": len(issues),
            "unanimous": sum(1 for i in issues if i.agreement == result.review.committee_size),
            "corroborated": sum(1 for i in issues if i.agreement >= 2),
            "contested": sum(1 for i in issues if i.contested),
            "suppressed_by_lead": result.suppressed,
            "severity": {
                level: sum(1 for i in issues if i.severity == level)
                for level in ("high", "medium", "low")
            },
            # Per-reviewer contribution: which models are worth their cost.
            "raised_by": {
                model: sum(
                    1 for i in issues if any(f.model_id == model for f in i.findings)
                )
                for model in reviewers
            },
            "consolidated_by": result.review.method,
            "fix_offered": bool(result.review.fixed_code),
            "fix_status": result.verdict.label if result.verdict else "none",
            "elapsed_ms": elapsed_ms,
            # Tokens per model, and the cost that follows from them. Rates are
            # whatever the config says, so the arithmetic can be re-checked
            # against a real invoice later.
            "tokens": {m: {"in": i, "out": o} for m, (i, o) in (usage or {}).items()},
            "cost_usd": _cost(usage, prices),
        }
        _write(event)
    except Exception:
        pass  # a broken counter must never cost the user a review


def load(path: Path | None = None) -> list[dict]:
    target = path or EVENTS
    if not target.exists():
        return []
    rows = []
    for line in target.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def now_ms() -> int:
    return int(time.monotonic() * 1000)
