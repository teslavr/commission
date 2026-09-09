"""Generates the metrics page: one self-contained HTML file, no build step.

Charts are inline SVG and all styles are inline, so the output can be committed
to `docs/` and served by GitHub Pages directly.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone

from .metrics import Metrics

CSS = """
:root {
  --bg:#f6f7f9; --panel:#fff; --ink:#14181f; --muted:#5f6875; --line:#e2e6eb;
  --accent:#1f5fa8; --good:#1a7f5a; --warn:#a8631f; --grid:#eef1f5;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg:#0f1216; --panel:#171b21; --ink:#e8ecf1; --muted:#98a2b0; --line:#262c35;
    --accent:#6aa9e9; --good:#5fc79a; --warn:#e0a458; --grid:#1e242c;
  }
}
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
  font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
.wrap { max-width:1040px; margin:0 auto; padding:40px 24px 72px; }
header { border-bottom:1px solid var(--line); padding-bottom:20px; margin-bottom:8px; }
h1 { font-size:1.5rem; font-weight:650; margin:0 0 6px; letter-spacing:-.01em; }
.sub { color:var(--muted); font-size:.9rem; margin:0; max-width:70ch; }
h2 { font-size:.78rem; font-weight:650; text-transform:uppercase; letter-spacing:.09em;
  color:var(--muted); margin:36px 0 14px; }
.grid { display:grid; gap:12px; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); }
.card { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px 18px; }
.n { font-size:1.9rem; font-weight:650; letter-spacing:-.02em; line-height:1.15;
  font-variant-numeric:tabular-nums; }
.k { font-size:.82rem; font-weight:600; margin-top:2px; }
.q { font-size:.79rem; color:var(--muted); margin-top:8px; line-height:1.45; }
.accent { color:var(--accent); } .good { color:var(--good); } .warn { color:var(--warn); }
.scroll { overflow-x:auto; background:var(--panel); border:1px solid var(--line); border-radius:8px; }
table { width:100%; border-collapse:collapse; font-size:.86rem; }
th,td { text-align:left; padding:9px 14px; border-bottom:1px solid var(--line); white-space:nowrap; }
tr:last-child td { border-bottom:none; }
th { font-size:.72rem; text-transform:uppercase; letter-spacing:.07em; color:var(--muted);
  background:var(--grid); font-weight:600; }
td.num { text-align:right; font-variant-numeric:tabular-nums; }
code { font:12.5px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace; }
.bar { height:6px; background:var(--grid); border-radius:3px; overflow:hidden; min-width:80px; }
.bar > i { display:block; height:100%; background:var(--accent); }
.note { background:var(--panel); border:1px solid var(--line); border-left:3px solid var(--accent);
  border-radius:6px; padding:14px 16px; font-size:.85rem; color:var(--muted); margin-top:28px; }
footer { margin-top:48px; padding-top:16px; border-top:1px solid var(--line);
  color:var(--muted); font-size:.8rem; }
.empty { background:var(--panel); border:1px dashed var(--line); border-radius:8px;
  padding:36px; text-align:center; color:var(--muted); }
"""

_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Metrics — The Commission</title>
<style>{css}</style></head>
<body><div class="wrap">
<header>
<h1>The Commission — metrics</h1>
<p class="sub">Aggregated from the review event log. Each record contains counts only:
an anonymous install id, which models ran, what they agreed on, and what it cost.
No source code, file paths, repository names, or finding text are recorded.</p>
</header>
{body}
<footer>Generated {generated} · {runs} review{plural} on record</footer>
</div></body></html>"""


def _card(value, label, definition, cls="") -> str:
    return (
        f'<div class="card"><div class="n {cls}">{value}</div>'
        f'<div class="k">{html.escape(label)}</div>'
        f'<div class="q">{html.escape(definition)}</div></div>'
    )


def _pct(x: float) -> str:
    return f"{round(x * 100)}%"


def render(m: Metrics) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if not m.runs:
        body = ('<div class="empty">No reviews recorded yet. Run '
                '<code>commish review &lt;file&gt;</code> to populate this page.</div>')
        return _TEMPLATE.format(css=CSS, generated=generated, body=body, runs=0, plural="s")

    p = []

    p.append("<h2>Cross-model agreement</h2><div class='grid'>")
    p.append(_card(_pct(m.corroboration_rate), "Corroborated findings",
                   "Share of published findings raised independently by two or more reviewers. "
                   "The core assumption: if independent models do not converge, the confidence "
                   "score carries no information.", "accent"))
    p.append(_card(_pct(m.unanimity_rate), "Unanimous findings",
                   "Raised by every reviewer that completed the run."))
    p.append(_card(_pct(m.contested_rate), "Contested findings",
                   "Corroborated by reviewers but rejected by the lead model, and published "
                   "anyway. Measures whether the consensus rule adds signal or noise.", "warn"))
    p.append(_card(m.suppressed_by_lead, "Suppressed",
                   "Single-reviewer findings the lead model rejected. Permitted below the "
                   "consensus threshold."))
    p.append("</div>")

    p.append("<h2>Fix quality</h2><div class='grid'>")
    p.append(_card(_pct(m.fix_offer_rate), "Reviews with a fix",
                   "Share of reviews that produced a concrete corrected file."))
    p.append(_card(_pct(m.fix_verified_rate), "Fixes verified",
                   "Share of proposed fixes that parsed and passed the configured check. "
                   "Unverified fixes are withheld. Proxy for merge rate until merge tracking "
                   "exists.", "good"))
    p.append(_card(m.total_issues, "Findings published", "Total across all reviews."))
    p.append(_card(f"{m.median_seconds}s", "Median duration", "Wall clock, full reviewer set."))
    p.append("</div>")

    p.append("<h2>Cost</h2><div class='grid'>")
    p.append(_card(f"${m.median_cost:.4f}", "Median per review",
                   "At the rates configured in .commish.yml. Bedrock pricing varies by region, "
                   "so treat this as arithmetic on your own numbers, not a quote."))
    p.append(_card(f"${m.cost_per_finding:.4f}", "Per finding published",
                   "Total spend divided by findings that reached the reader."))
    p.append(_card(f"${m.total_cost:.2f}", "Total recorded",
                   f"Across the {m.priced_runs} review(s) that carry token data."))
    p.append(_card(f"{sum(d.get('tokens', 0) for d in m.per_reviewer.values()):,}", "Reviewer tokens",
                   "Input plus output, reviewers only."))
    p.append("</div>")

    p.append("<h2>Adoption and retention</h2><div class='grid'>")
    p.append(_card(m.users, "Installs", "Distinct anonymous install identifiers."))
    p.append(_card(m.runs, "Reviews", "Total reviews run."))
    p.append(_card(m.runs_per_user, "Reviews per install",
                   "Trial-only usage sits near 1.0 and does not move."))
    p.append(_card(_pct(m.repeat_user_rate), "Repeat rate",
                   "Installs with more than one review. Primary retention signal and a stated "
                   "kill criterion.", "accent"))
    p.append("</div>")

    if m.per_reviewer:
        p.append("<h2>Reviewer performance</h2><div class='scroll'><table>")
        p.append("<tr><th>Model</th><th class='num'>Runs</th><th class='num'>Findings</th>"
                 "<th class='num'>Per run</th><th class='num'>Failures</th>"
                 "<th class='num'>Tokens</th><th>Relative yield</th></tr>")
        peak = max((d["findings_per_run"] for d in m.per_reviewer.values()), default=1) or 1
        for model, d in sorted(m.per_reviewer.items(),
                               key=lambda kv: kv[1]["findings_per_run"], reverse=True):
            width = round(100 * d["findings_per_run"] / peak)
            p.append(
                f"<tr><td><code>{html.escape(model)}</code></td>"
                f"<td class='num'>{d['runs']}</td><td class='num'>{d['findings']}</td>"
                f"<td class='num'>{d['findings_per_run']}</td>"
                f"<td class='num'>{d['failures']}</td>"
                f"<td class='num'>{d.get('tokens', 0):,}</td>"
                f"<td><div class='bar'><i style='width:{width}%'></i></div></td></tr>"
            )
        p.append("</table></div>")
        p.append('<div class="note">Yield per run and failure rate determine which models '
                 'justify their cost. This is the input to routing: a model that contributes '
                 'few unique findings, or fails to return usable output, can be dropped from '
                 'the default set without weakening cross-vendor coverage.</div>')

    if m.failures:
        p.append("<h2>Reviewer failures by cause</h2><div class='scroll'><table>")
        p.append("<tr><th>Cause</th><th class='num'>Occurrences</th></tr>")
        for reason, count in m.failures.most_common():
            p.append(f"<tr><td><code>{html.escape(reason)}</code></td>"
                     f"<td class='num'>{count}</td></tr>")
        p.append("</table></div>")

    if m.severity:
        p.append("<h2>Findings by severity</h2><div class='scroll'><table>")
        p.append("<tr><th>Severity</th><th class='num'>Findings</th></tr>")
        for level in ("high", "medium", "low"):
            if m.severity.get(level):
                p.append(f"<tr><td>{level}</td><td class='num'>{m.severity[level]}</td></tr>")
        p.append("</table></div>")

    if m.surfaces:
        p.append("<h2>Invocation surface</h2><div class='scroll'><table>")
        p.append("<tr><th>Surface</th><th class='num'>Reviews</th></tr>")
        for surface, count in m.surfaces.most_common():
            p.append(f"<tr><td>{html.escape(surface)}</td><td class='num'>{count}</td></tr>")
        p.append("</table></div>")

    return _TEMPLATE.format(css=CSS, generated=generated, body="\n".join(p),
                            runs=m.runs, plural="" if m.runs == 1 else "s")
