"""Aggregation of the event log into the metrics named in the strategy doc.

Each metric answers a question that was written down before the data existed,
and each maps to a decision: ship, tune, or kill.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field


@dataclass
class Metrics:
    runs: int = 0
    users: int = 0
    files_reviewed: int = 0
    total_issues: int = 0
    # Do independent vendors describe the same defect similarly enough to be
    # matched? If this collapses, the confidence score is meaningless. First kill signal.
    corroboration_rate: float = 0.0
    unanimity_rate: float = 0.0
    # Findings the lead model rejected but the consensus rule kept. Measures
    # whether that rule adds signal or noise.
    contested_rate: float = 0.0
    suppressed_by_lead: int = 0
    # Share of proposed fixes that survive mechanical verification. Proxy for the
    # north-star metric (merge rate) until merge tracking exists.
    fix_offer_rate: float = 0.0
    fix_verified_rate: float = 0.0
    # Retention.
    runs_per_user: float = 0.0
    repeat_user_rate: float = 0.0
    median_seconds: float = 0.0
    total_cost: float = 0.0
    median_cost: float = 0.0
    cost_per_finding: float = 0.0
    priced_runs: int = 0
    per_reviewer: dict = field(default_factory=dict)
    failures: Counter = field(default_factory=Counter)
    severity: Counter = field(default_factory=Counter)
    surfaces: Counter = field(default_factory=Counter)
    by_day: dict = field(default_factory=dict)


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def compute(events: list[dict]) -> Metrics:
    m = Metrics()
    if not events:
        return m

    m.runs = len(events)
    per_user = Counter(e.get("install_id", "unknown") for e in events)
    m.users = len(per_user)
    m.runs_per_user = round(m.runs / m.users, 1)
    m.repeat_user_rate = round(sum(1 for n in per_user.values() if n > 1) / m.users, 2)
    m.files_reviewed = m.runs

    issues = sum(e.get("issues_published", 0) for e in events)
    m.total_issues = issues
    if issues:
        m.corroboration_rate = round(sum(e.get("corroborated", 0) for e in events) / issues, 2)
        m.unanimity_rate = round(sum(e.get("unanimous", 0) for e in events) / issues, 2)
        m.contested_rate = round(sum(e.get("contested", 0) for e in events) / issues, 2)
    m.suppressed_by_lead = sum(e.get("suppressed_by_lead", 0) for e in events)

    offered = [e for e in events if e.get("fix_offered")]
    m.fix_offer_rate = round(len(offered) / m.runs, 2)
    if offered:
        m.fix_verified_rate = round(
            sum(1 for e in offered if e.get("fix_status") == "verified") / len(offered), 2
        )

    m.median_seconds = round(_median([e.get("elapsed_ms", 0) / 1000 for e in events]), 1)

    # Only events that actually carry cost data. Averaging in records written
    # before token tracking existed would quietly halve every figure.
    costs = [c for c in (e.get("cost_usd", 0.0) for e in events) if c > 0]
    priced_issues = sum(
        e.get("issues_published", 0) for e in events if e.get("cost_usd", 0.0) > 0
    )
    m.total_cost = round(sum(costs), 4)
    m.median_cost = round(_median(costs), 4)
    m.priced_runs = len(costs)
    if priced_issues:
        m.cost_per_finding = round(sum(costs) / priced_issues, 4)

    seated: Counter = Counter()
    raised: Counter = Counter()
    failed: Counter = Counter()
    spend: Counter = Counter()
    for e in events:
        for model in e.get("reviewers", []):
            seated[model] += 1
        for model, count in (e.get("raised_by") or {}).items():
            raised[model] += count
        for model, reason in (e.get("reviewers_failed") or {}).items():
            failed[model] += 1
            m.failures[reason] += 1
        for model, tok in (e.get("tokens") or {}).items():
            spend[model] += tok.get("in", 0) + tok.get("out", 0)
        for level, count in (e.get("severity") or {}).items():
            m.severity[level] += count
        m.surfaces[e.get("surface", "unknown")] += 1
        day = (e.get("ts") or "")[:10]
        if day:
            m.by_day[day] = m.by_day.get(day, 0) + 1

    # Per-reviewer yield and reliability: which models justify their cost.
    m.per_reviewer = {
        model: {
            "runs": seated[model],
            "findings": raised.get(model, 0),
            "findings_per_run": round(raised.get(model, 0) / seated[model], 2) if seated[model] else 0.0,
            "failures": failed.get(model, 0),
            "failure_rate": round(failed.get(model, 0) / seated[model], 2) if seated[model] else 0.0,
            "tokens": spend.get(model, 0),
        }
        for model in seated
    }
    return m
