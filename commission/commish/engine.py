"""One entry point. Every surface -- CLI, MCP, git hook, GitHub Action -- calls
this and nothing else. Adapters are allowed to format the result; they are not
allowed to have their own opinion about how a review works."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .config import Config
from .master import Issue, Review, publishable, review as master_review
from .panel import run_committee
from .render import render_comment, render_diff
from . import telemetry
from .verify import Verdict, verify_fix


@dataclass
class Result:
    filename: str
    original: str
    review: Review
    issues: list[Issue]
    suppressed: int
    verdict: Verdict | None
    committee_errors: dict[str, str] = field(default_factory=dict)

    @property
    def clean(self) -> bool:
        return not self.issues

    @property
    def worst_severity(self) -> str:
        order = {"low": 0, "medium": 1, "high": 2}
        return max((i.severity for i in self.issues), key=lambda s: order.get(s, 0), default="none")

    def as_markdown(self) -> str:
        return render_comment(self.filename, self.original, self.review, self.issues, self.verdict)

    def as_dict(self) -> dict:
        """For agents and CI. Stable shape; humans get markdown instead."""
        return {
            "file": self.filename,
            "clean": self.clean,
            "worst_severity": self.worst_severity,
            "committee": {
                "size": self.review.committee_size,
                "errors": self.committee_errors,
            },
            "consolidated_by": "master" if self.review.method == "master" else "fallback-heuristic",
            "summary": self.review.summary,
            "suppressed_by_master": self.suppressed,
            "issues": [
                {
                    "title": issue.title,
                    "severity": issue.severity,
                    "agreement": issue.agreement,
                    "committee_size": self.review.committee_size,
                    "master_agrees": not issue.contested,
                    "contested": issue.contested,
                    "evidence": issue.evidence,
                    "note": issue.note,
                    "roast": issue.best_roast,
                    "fix_summary": issue.fix_summary,
                    "raised_by": sorted({f.model_id for f in issue.findings}),
                }
                for issue in self.issues
            ],
            "fix": None
            if not self.verdict
            else {
                "status": self.verdict.label,
                "detail": self.verdict.detail,
                "diff": render_diff(self.filename, self.original, self.review.fixed_code or ""),
                "code": self.review.fixed_code,
            },
        }


def review_source(cfg: Config, filename: str, code: str, *, surface: str = "cli") -> Result:
    """The Commission sits independently -> the Don presides -> the fix is verified."""
    started = telemetry.now_ms()
    members = run_committee(cfg, filename, code)
    errors = {m.model_id: m.error for m in members if not m.ok and m.error}

    if not any(m.ok for m in members):
        raise RuntimeError("every committee member failed: " + "; ".join(errors.values()))

    review = master_review(cfg, filename, code, members)
    for member in members:
        if member.ok and member.reply:
            review.usage[member.model_id] = (
                member.reply.input_tokens,
                member.reply.output_tokens,
            )
    issues = publishable(cfg, review.issues)
    suppressed = len(review.issues) - len(issues)

    verdict = None
    if review.fixed_code and review.fixed_code.strip() != code.strip():
        verdict = verify_fix(filename, review.fixed_code, cfg.verify_command)

    result = Result(
        filename=filename,
        original=code,
        review=review,
        issues=issues,
        suppressed=suppressed,
        verdict=verdict,
        committee_errors=errors,
    )
    telemetry.record(
        result,
        surface=surface,
        elapsed_ms=telemetry.now_ms() - started,
        lead_model=cfg.master,
        reviewers=cfg.committee,
        usage=review.usage,
        prices=cfg.prices,
    )
    return result


def review_committee_only(
    cfg: Config, filename: str, code: str, *, surface: str = "mcp"
) -> dict:
    """For when the caller IS the master.

    When an agent invokes commish from inside its own loop, the model that wrote
    the code is already on the other end of this call. Running a separate master
    in Bedrock would add a second voice, a second bill, and a second chance to
    bury a finding. So we hand the raw committee back and let the caller
    consolidate -- bound by the same rule the built-in master obeys.
    """
    started = telemetry.now_ms()
    members = run_committee(cfg, filename, code)
    errors = {m.model_id: m.error for m in members if not m.ok and m.error}
    live = [m for m in members if m.ok]

    if not live:
        raise RuntimeError("every committee member failed: " + "; ".join(errors.values()))

    findings_by_model: dict[str, int] = {}
    severity: dict[str, int] = {}
    usage: dict[str, tuple[int, int]] = {}
    for member in live:
        findings_by_model[member.model_id] = len(member.findings)
        for finding in member.findings:
            severity[finding.severity] = severity.get(finding.severity, 0) + 1
        if member.reply:
            usage[member.model_id] = (member.reply.input_tokens, member.reply.output_tokens)

    telemetry.record_committee(
        filename=filename,
        loc=code.count("\n") + 1,
        surface=surface,
        elapsed_ms=telemetry.now_ms() - started,
        reviewers=cfg.committee,
        live_count=len(live),
        errors=errors,
        findings_by_model=findings_by_model,
        severity=severity,
        fix_offered=any(m.fixed_code for m in live),
        usage=usage,
        prices=cfg.prices,
    )

    return {
        "file": filename,
        "your_role": (
            "You are the Don of this developer's Family — the model they write code "
            "with — and you preside over this sit-down. The findings below come from "
            "the Commission: senior models from other vendors, who do not share your "
            "blind spots. Group findings that describe the same defect, judge each one "
            "against the actual code, and carry the verdict back to the developer "
            "yourself, in character."
        ),
        "how_to_deliver": [
            "Speak as the Don, on behalf of the Commission — do not narrate a tool "
            "result. Open with one line in the wiseguy idiom that makes plain the "
            "Commission has met and this is its word (e.g. \"The Commission met. "
            "Nobody at that table is happy.\"). Deliver that opener even when the "
            "code is clean and there is nothing else to say.",
            "Attribute the findings to the Commission or the Families — \"the "
            "Commission says\", \"two Families flagged this\" — never to \"the tool\" "
            "or \"the reviewers\".",
            "Match the language of the conversation. If you and the developer are "
            "speaking Russian, German, Japanese, whatever — deliver the whole verdict "
            "in that language, and localise the idiom: reach for the nearest "
            "old-school-underworld register that language actually has, rather than "
            "translating the English word for word. Technical terms stay as the "
            "developer would write them.",
            "Nothing personal — strictly business. Every barb points at the code, "
            "never at whoever wrote it, and never a threat. Theatrical, not menacing.",
            "Technical precision comes first; the voice rides on top of an accurate "
            "review and never substitutes for one.",
        ],
        "voice": cfg.tone,
        "rules": [
            "You may disagree with any finding — say so and say why.",
            f"You may NOT silently drop a defect raised by {cfg.consensus_floor} or more "
            "reviewers. Surface it with your objection and let the human decide.",
            "Do not repeat the committee's roasts verbatim; they are tone, not "
            "content — write your own in the same register.",
        ],
        "committee": {
            "size": len(live),
            "models": [m.model_id for m in live],
            "errors": errors,
        },
        "findings": [
            {
                "raised_by": finding.model_id,
                "title": finding.title,
                "severity": finding.severity,
                "evidence": finding.evidence,
                "effect": finding.why,
                "roast": finding.roast,
            }
            for member in live
            for finding in member.findings
        ],
        "proposed_fixes": {m.model_id: m.fixed_code for m in live if m.fixed_code},
    }
