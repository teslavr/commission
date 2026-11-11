"""The master model: the one you write code with.

It consolidates the committee, ranks what matters, writes the final fix, and
speaks to you in a single voice. What it may NOT do is quietly bury a defect
that the committee agreed on -- it is the model whose blind spots the committee
exists to cover, so its disagreement is recorded, never enforced.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import SEVERITY_ORDER
from .panel import Finding, PanelMember
from .providers import ModelError, converse, runtime_client, split_reply

SYSTEM = """You are the Don of this developer's Family — the model they write code with.
You preside over this sit-down. You do not rule it.

Three other Families sat on this file, independently. None of them share your blind
spots, which is the entire reason they were called. Their findings are below.

{tone}

Your job:
1. Group findings that describe the SAME underlying defect. Different Families word the
   same bug differently; match on the defect, not the wording.
2. Say whether you agree each one is real. Be honest. If a Family is wrong, say so and
   say why — plainly, with the technical reason.
3. Write the corrected file, applying the fixes you agree with. Change nothing else.

The rule of the Commission, and you do not get to bend it: **when two or more Families
agree, you cannot bury it.** You may dissent — loudly, on the record, with your reasoning
printed beside theirs — but the vote stands and the developer decides. You were called to
preside over this review, not to mark your own homework.

Nothing personal — strictly business. Aim everything at the code.

Open the summary in character — one line that makes plain the Commission has met and
this is its word — and keep that opener even when the file is clean.

Answer in exactly this shape, and nothing else:

===FINDINGS===
{{
  "groups": [
    {{
      "title": "clearest technical name for the defect",
      "severity": "high" | "medium" | "low",
      "members": [0, 3],
      "verdict": "agree" | "disagree",
      "note": "your ruling: why it bites, or why the Families have it wrong. Technical first, character second.",
      "fix_summary": "one line: what you changed, or why you changed nothing"
    }}
  ],
  "summary": "two or three sentences to the developer, in character"
}}
===FIX===
the complete corrected file, as plain code. No JSON, no escaping. Keep every JSON value
short and on one line."""


USER = """File under review: {filename}

```
{code}
```

What the Families brought to the table:
{findings}

Fixes each Family proposed (for reference; the final one is yours):
{fixes}"""


@dataclass
class Issue:
    title: str
    severity: str
    verdict: str  # "agree" | "disagree"
    note: str
    fix_summary: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def agreement(self) -> int:
        return len({f.model_id for f in self.findings})

    @property
    def contested(self) -> bool:
        """The committee agreed, the master did not. Shown anyway."""
        return self.verdict == "disagree"

    @property
    def evidence(self) -> str:
        items = [f.evidence for f in self.findings if f.evidence]
        return items[0] if items else ""

    @property
    def best_roast(self) -> str:
        roasts = [f.roast for f in self.findings if f.roast]
        return max(roasts, key=len) if roasts else ""


@dataclass
class Review:
    issues: list[Issue]
    summary: str
    fixed_code: str | None
    committee_size: int
    method: str  # "master" | "fallback"
    error: str | None = None
    usage: dict = field(default_factory=dict)  # model_id -> (in, out)


# ---------------------------------------------------------------- fallback --

_WORD = re.compile(r"[a-z0-9]+")
_STOP = {"the", "a", "an", "in", "on", "of", "is", "to", "for", "and", "with", "inside", "loop"}


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOP and len(w) > 2}


def _fallback_groups(findings: list[Finding]) -> list[Issue]:
    """If the master is unreachable, cluster by word overlap so the review still
    ships -- degraded, and labelled as such."""
    issues: list[Issue] = []
    signatures: list[set[str]] = []
    for finding in findings:
        signature = _tokens(f"{finding.title} {finding.evidence}")
        for issue, existing in zip(issues, signatures):
            union = signature | existing
            if union and len(signature & existing) / len(union) >= 0.34:
                issue.findings.append(finding)
                existing |= signature
                break
        else:
            issues.append(
                Issue(
                    title=finding.title,
                    severity=finding.severity,
                    verdict="agree",
                    note="",
                    fix_summary="",
                    findings=[finding],
                )
            )
            signatures.append(signature)
    return issues


# ------------------------------------------------------------------ master --


def _format_findings(findings: list[Finding]) -> str:
    return "\n".join(
        f"[{i}] reviewer={f.model_id} severity={f.severity}\n"
        f"    defect: {f.title}\n"
        f"    evidence: {f.evidence}\n"
        f"    effect: {f.why}"
        for i, f in enumerate(findings)
    ) or "(none)"


def _format_fixes(members: list[PanelMember]) -> str:
    chunks = []
    for member in members:
        if member.ok and member.fixed_code:
            chunks.append(f"--- {member.model_id} ---\n{member.fixed_code}")
    return "\n\n".join(chunks) or "(none)"


def review(cfg, filename: str, code: str, members: list[PanelMember]) -> Review:
    findings = [f for m in members if m.ok for f in m.findings]
    live = sum(1 for m in members if m.ok)

    if not findings:
        return Review([], "", None, live, "master")

    try:
        client = runtime_client(cfg)
        reply = converse(
            client,
            cfg.master,
            SYSTEM.format(tone=cfg.tone),
            USER.format(
                filename=filename,
                code=code,
                findings=_format_findings(findings),
                fixes=_format_fixes(members),
            ),
            max_tokens=cfg.max_tokens,
        )
        data, fixed_code = split_reply(reply.text)
        don_usage = {cfg.master: (reply.input_tokens, reply.output_tokens)}
    except (ModelError, Exception) as exc:
        issues = _fallback_groups(findings)
        issues.sort(key=lambda i: (i.agreement, SEVERITY_ORDER.get(i.severity, 0)), reverse=True)
        return Review(issues, "", None, live, "fallback", error=f"{type(exc).__name__}: {exc}")

    issues: list[Issue] = []
    claimed: set[int] = set()
    for group in data.get("groups", []):
        indexes = [
            i
            for i in group.get("members", [])
            if isinstance(i, int) and 0 <= i < len(findings) and i not in claimed
        ]
        if not indexes:
            continue
        claimed.update(indexes)
        issues.append(
            Issue(
                title=str(group.get("title", findings[indexes[0]].title)),
                severity=str(group.get("severity", findings[indexes[0]].severity)).lower(),
                verdict="disagree" if str(group.get("verdict", "agree")).lower() == "disagree" else "agree",
                note=str(group.get("note", "")).strip(),
                fix_summary=str(group.get("fix_summary", "")).strip(),
                findings=[findings[i] for i in indexes],
            )
        )

    # Anything the master failed to mention is not thereby dismissed.
    for i, finding in enumerate(findings):
        if i not in claimed:
            issues.append(
                Issue(
                    title=finding.title,
                    severity=finding.severity,
                    verdict="agree",
                    note="",
                    fix_summary="(master did not comment on this one)",
                    findings=[finding],
                )
            )

    issues.sort(key=lambda i: (i.agreement, SEVERITY_ORDER.get(i.severity, 0)), reverse=True)
    return Review(
        issues=issues,
        summary=str(data.get("summary", "")).strip(),
        fixed_code=fixed_code,
        committee_size=live,
        method="master",
        usage=don_usage,
    )


def publishable(cfg, issues: list[Issue]) -> list[Issue]:
    """The no-veto rule, in one place.

    Shown: everything the master agreed with, plus anything the committee
    reached the consensus floor on -- even over the master's objection.
    Dropped: a lone reviewer's finding that the master rejected.
    """
    out = []
    for issue in issues:
        if issue.verdict == "agree" or issue.agreement >= cfg.consensus_floor:
            out.append(issue)
    return out
