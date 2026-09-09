"""Render the review as the PR comment a developer actually reads."""
from __future__ import annotations

import difflib

from .master import Issue, Review
from .verify import Verdict

SEVERITY_BADGE = {"high": "🔴 high", "medium": "🟠 medium", "low": "⚪ low"}


def _confidence(issue: Issue, committee_size: int) -> str:
    ratio = f"{issue.agreement}/{committee_size}"
    if issue.agreement == committee_size and committee_size > 1:
        vote = f"the Commission is unanimous ({ratio})"
    else:
        vote = f"the Commission votes {ratio}"
    return f"{vote} · **the Don dissents**" if issue.contested else f"{vote} · the Don concurs"


def render_issue(issue: Issue, committee_size: int) -> str:
    lines = [
        f"### {SEVERITY_BADGE.get(issue.severity, issue.severity)} — {issue.title}",
        f"<sub>{_confidence(issue, committee_size)}</sub>",
        "",
    ]
    if issue.best_roast:
        lines += [f"> {issue.best_roast}", ""]
    if issue.evidence:
        lines += ["```", issue.evidence, "```", ""]
    if issue.note:
        label = "The Don, dissenting" if issue.contested else "The Don"
        lines += [f"**{label}:** {issue.note}", ""]
    if issue.contested:
        lines += [
            "_The Families agreed and the Don did not. It stands anyway — he presides "
            "over the Commission, he does not overrule it. Your call._",
            "",
        ]
    if issue.fix_summary:
        lines += [f"**Fix:** {issue.fix_summary}", ""]
    return "\n".join(lines)


def render_diff(filename: str, before: str, after: str) -> str:
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
    )
    return "".join(diff)


def render_comment(
    filename: str,
    original: str,
    review: Review,
    issues: list[Issue],
    verdict: Verdict | None,
) -> str:
    parts = ["## 🎩 The Commission — a sit-down", ""]

    if not issues:
        parts += [
            "Nothing on the table. The Commission looked and found no business worth "
            "calling a sit-down over. Read nothing into the silence — it is not praise.",
            "",
        ]
    else:
        if review.summary:
            parts += [review.summary, ""]
        parts += [
            f"<sub>{review.committee_size} Families sat on this — each a different model "
            f"from a different vendor. Presided over by your own.</sub>",
            "",
            "---",
            "",
        ]
        for issue in issues:
            parts.append(render_issue(issue, review.committee_size))

    if review.fixed_code and review.fixed_code.strip() != original.strip():
        patch = render_diff(filename, original, review.fixed_code)
        if patch:
            badge = {
                "verified": "✅ **the fix stands** — ",
                "unverified": "⚠️ **unvouched for** — ",
                "broken": "❌ **it sleeps with the fishes** — ",
            }.get(verdict.label if verdict else "unverified", "")
            detail = verdict.detail if verdict else ""
            parts += ["---", "", "### The offer", "", f"{badge}{detail}", ""]
            if verdict is None or verdict.ok:
                parts += ["```diff", patch.rstrip(), "```", ""]

    if review.method == "fallback":
        parts += [
            "---",
            "",
            f"<sub>⚠️ The Don never showed ({review.error}). The Families' findings "
            f"were grouped by a text heuristic and nobody presided. Treat the vote "
            f"counts with suspicion.</sub>",
            "",
        ]

    return "\n".join(parts).rstrip() + "\n"
