"""commish — the Commission sits on your code. Your own Don presides.

    commish review orders.py
    commish review orders.py --lines 40-90
    cat snippet.py | commish review -
    commish review --staged
    commish review orders.py --format json     # for agents and CI
    commish mcp                                # serve over MCP (any agent)
    commish --provider openrouter review x.py  # Bedrock or OpenRouter

Exit codes: 0 = clean, 1 = findings at or above --fail-on, 2 = could not run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Config, vendor_of
from .engine import Result, review_source
from .preflight import (
    access_denied_message,
    check,
    first_run_message,
    is_first_run,
    no_credentials_message,
)
from .sources import Source, from_file, from_git, from_stdin

SEVERITY_ORDER = {"none": -1, "low": 0, "medium": 1, "high": 2}


def explain(failure: str, provider: str = "bedrock") -> str:
    """Turn a wall of vendor exceptions into the one sentence that helps."""
    lowered = failure.lower()
    if ("nocredentials" in lowered or "unable to locate credentials" in lowered
            or "unauthorized" in lowered):
        return no_credentials_message(provider)
    if any(k in lowered for k in ("accessdenied", "not available for this account",
                                   "insufficientcredits")):
        return access_denied_message(provider)
    return f"commish: {failure}"


def build_config(args) -> Config:
    cfg = Config.load(getattr(args, "config", None))
    if getattr(args, "provider", None):
        cfg.provider = args.provider
    if getattr(args, "master", None):
        cfg.master = args.master
        cfg._auto_committee = True
    if getattr(args, "committee", None):
        cfg.committee = args.committee
        cfg._auto_committee = False
    return cfg.finalize()


def collect_sources(args) -> list[Source]:
    if args.staged or args.diff:
        return from_git(staged=args.staged)
    if args.path == "-":
        return [from_stdin(args.filename)]
    if args.path:
        return [from_file(args.path, args.lines)]
    raise ValueError("give a path, `-` for stdin, or --staged / --diff")


def emit(results: list[Result], fmt: str, out: str | None) -> None:
    if fmt == "json":
        payload = json.dumps([r.as_dict() for r in results], indent=2)
    else:
        payload = "\n\n---\n\n".join(r.as_markdown() for r in results)
    if out:
        Path(out).write_text(payload)
        print(f"written to {out}", file=sys.stderr)
    else:
        print(payload)


def cmd_review(args) -> int:
    cfg = build_config(args)
    blocked = check(cfg.provider)
    if blocked:
        print(blocked, file=sys.stderr)
        return 2
    first = is_first_run()
    try:
        sources = collect_sources(args)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"commish: {exc}", file=sys.stderr)
        return 2

    if not sources:
        print("commish: nothing to review", file=sys.stderr)
        return 0

    if not args.quiet:
        if first:
            print(first_run_message(cfg.provider), file=sys.stderr)
        print(
            f"the Don:        {cfg.master} ({vendor_of(cfg.master)})\n"
            f"the Commission: {', '.join(cfg.committee)}\n"
            f"via:            {cfg.where}",
            file=sys.stderr,
        )

    results: list[Result] = []
    for source in sources:
        if not args.quiet:
            print(f"\nreviewing {source.label}", file=sys.stderr)
        try:
            result = review_source(cfg, source.label, source.code, surface="cli")
        except RuntimeError as exc:
            print(explain(str(exc), cfg.provider), file=sys.stderr)
            return 2
        if not args.quiet:
            for model, error in result.committee_errors.items():
                print(f"  · {model}: FAILED — {error}", file=sys.stderr)
            print(
                f"  · {len(result.issues)} issue(s), worst={result.worst_severity}"
                + (f", {result.suppressed} struck by the Don" if result.suppressed else ""),
                file=sys.stderr,
            )
            if result.verdict:
                print(f"  · fix: {result.verdict.label} — {result.verdict.detail}", file=sys.stderr)
        results.append(result)

    if not args.quiet:
        print(file=sys.stderr)
    emit(results, args.format, args.out)

    floor = SEVERITY_ORDER.get(args.fail_on, 99)
    worst = max((SEVERITY_ORDER.get(r.worst_severity, -1) for r in results), default=-1)
    return 1 if worst >= floor else 0


def cmd_doctor(args) -> int:
    """Answer one question: will a review work right now, and if not, why."""
    from concurrent.futures import ThreadPoolExecutor

    from .preflight import credential_source, credentials_present, load_env_file
    from .providers import ModelError, converse, runtime_client

    load_env_file()
    cfg = build_config(args)
    ok = True

    print(f"credentials — provider {cfg.provider}")
    if credentials_present(cfg.provider):
        print(f"  ✅ found ({credential_source(cfg.provider)}), via {cfg.where}")
    else:
        print("  ❌ none found")
        print(no_credentials_message(cfg.provider), file=sys.stderr)
        return 2

    print("\nmodels — one cheap call each")
    client = runtime_client(cfg)

    def probe(model: str) -> tuple[str, bool, str]:
        try:
            converse(client, model, "Reply with one word.",
                     "Say OK", max_tokens=200)
            return model, True, ""
        except ModelError as exc:
            note = str(exc).split(":", 1)[-1].strip()
            return model, False, note[:80]
        except Exception as exc:
            return model, False, f"{type(exc).__name__}: {exc}"[:80]

    roles = [(cfg.master, "the Don")] + [(m, "Commission") for m in cfg.committee]
    with ThreadPoolExecutor(max_workers=max(1, len(roles))) as pool:
        results = list(pool.map(lambda r: probe(r[0]), roles))

    working_vendors = set()
    for (model, role), (_, good, note) in zip(roles, results):
        if good:
            print(f"  ✅ {model:<45} {role}")
            working_vendors.add(vendor_of(model))
        else:
            ok = False
            print(f"  ❌ {model:<45} {role}")
            print(f"     {note}")

    print("\nverdict")
    if ok:
        others = working_vendors - {vendor_of(cfg.master)}
        if len(others) >= 2:
            print(f"  ✅ ready — {len(others)} vendors on the Commission, plus your own model")
        else:
            ok = False
            print(f"  ⚠️  only {len(others)} vendor(s) besides your own can be reached.")
            print("     Agreement between models that share a vendor means little.")
            print("     Enable models from at least two others: commish models")
    else:
        notes = [note.lower() for _, good, note in results if not good]
        denied = any("not available" in n or "accessdenied" in n for n in notes)
        print("  ❌ not ready.")
        if cfg.provider == "openrouter":
            if any("insufficientcredits" in n for n in notes):
                print("     Out of credit — every model refuses at once: https://openrouter.ai/credits")
            if any("unauthorized" in n for n in notes):
                print("     The key was rejected — check OPENROUTER_API_KEY: https://openrouter.ai/keys")
            if denied:
                print("     A model refused you: a wrong id, or a key restricted by allowlist")
                print("     or privacy settings — https://openrouter.ai/settings/privacy")
            print("     `commish models` lists every id OpenRouter will take;")
        else:
            if denied:
                print("     A model refused you. Two possible causes, fixed in different places:")
                print("       · the key lacks permission — reissue it with AmazonBedrockFullAccess")
                print("       · the model is not enabled — Bedrock console → Model access")
            print("     `commish models` lists what this account and region offer;")
        print("     put the ids that answer into .commish.yml.")
    return 0 if ok else 1


def cmd_stats(args) -> int:
    """Review metrics, in the terminal."""
    from .metrics import compute
    from .telemetry import EVENTS, load

    m = compute(load(Path(args.log) if args.log else None))
    if not m.runs:
        print(f"No reviews recorded ({EVENTS}). Run a review first.")
        return 0
    pct = lambda x: f"{round(x * 100)}%"
    print(f"reviews {m.runs} · installs {m.users} · {m.runs_per_user} per install · "
          f"repeat rate {pct(m.repeat_user_rate)}")
    print(f"findings {m.total_issues} · corroborated {pct(m.corroboration_rate)} · "
          f"unanimous {pct(m.unanimity_rate)} · contested {pct(m.contested_rate)} · "
          f"suppressed {m.suppressed_by_lead}")
    print(f"fixes proposed {pct(m.fix_offer_rate)} · verified {pct(m.fix_verified_rate)} · "
          f"median {m.median_seconds}s")
    print(f"spend ${m.total_cost:.4f} total · ${m.median_cost:.4f} median per review · "
          f"${m.cost_per_finding:.4f} per finding")
    if m.per_reviewer:
        print("\nreviewer                                     runs  finds  /run  fail    tokens")
        for model, d in sorted(m.per_reviewer.items(),
                               key=lambda kv: kv[1]["findings_per_run"], reverse=True):
            print(f"  {model:<42} {d['runs']:>4} {d['findings']:>6} "
                  f"{d['findings_per_run']:>5} {d['failures']:>5} {d.get('tokens', 0):>9,}")
    if m.failures:
        print("\nfailures: " + ", ".join(f"{k}={v}" for k, v in m.failures.most_common()))
    return 0


def cmd_dashboard(args) -> int:
    """Render the metrics page as one self-contained file, for GitHub Pages."""
    from .dashboard import render
    from .metrics import compute
    from .telemetry import load

    page = render(compute(load(Path(args.log) if args.log else None)))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"written to {out} ({len(page):,} bytes)")
    return 0


def cmd_models(args) -> int:
    from .providers import list_available_models

    cfg = build_config(args)
    blocked = check(cfg.provider)
    if blocked:
        print(blocked, file=sys.stderr)
        return 2
    rows = list_available_models(cfg)
    if not rows:
        if cfg.provider == "openrouter":
            print("OpenRouter returned no models. Check the network, or OPENROUTER_BASE_URL.")
        else:
            print(f"No models visible in {cfg.region}. Enable model access in the Bedrock console.")
        return 2
    width = max(len(r["id"]) for r in rows)
    for row in sorted(rows, key=lambda r: (r["kind"], r["id"])):
        print(f"{row['id']:<{width}}  {row['kind']:<18}  {row['name']}")
    return 0


def cmd_mcp(args) -> int:
    from .mcp_server import serve

    cfg = build_config(args)
    blocked = check(cfg.provider)
    if blocked:
        # Keep serving: an agent should hear why its tool call failed rather
        # than watch the server vanish.
        print(blocked, file=sys.stderr)
    serve(cfg)
    return 0


def cmd_review_pr(args) -> int:
    from .github import GitHubError, changed_files, from_environment, upsert_comment

    cfg = build_config(args)
    blocked = check(cfg.provider)
    if blocked:
        print(blocked, file=sys.stderr)
        return 2
    try:
        pr = from_environment()
        files = changed_files(pr)
    except GitHubError as exc:
        print(f"commish: {exc}", file=sys.stderr)
        return 2

    if not files:
        print("commish: no reviewable files in this PR", file=sys.stderr)
        return 0

    reviewed, skipped = files[: args.max_files], files[args.max_files :]
    sections: list[str] = []
    worst = -1

    for name in reviewed:
        path = Path(name)
        if not path.is_file():
            print(f"  · {name}: not checked out, skipped", file=sys.stderr)
            continue
        try:
            result = review_source(cfg, name, path.read_text(), surface="github-action")
        except RuntimeError as exc:
            print(explain(str(exc), cfg.provider), file=sys.stderr)
            continue
        worst = max(worst, SEVERITY_ORDER.get(result.worst_severity, -1))
        if result.clean and not result.verdict:
            continue
        sections.append(
            f"<details open><summary><code>{name}</code></summary>\n\n"
            f"{result.as_markdown()}\n</details>"
        )

    if not sections:
        print("commish: nothing worth commenting on", file=sys.stderr)
        return 0

    body = "\n\n".join(sections)
    if skipped:
        # A cap must never read as full coverage.
        body += (
            f"\n\n<sub>Reviewed {len(reviewed)} of {len(files)} changed files. "
            "Not looked at: " + ", ".join(f"`{s}`" for s in skipped) + ".</sub>\n"
        )

    print(f"posted: {upsert_comment(pr, body)}", file=sys.stderr)
    return 1 if worst >= SEVERITY_ORDER.get(args.fail_on, 99) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="commish", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", help="path to .commish.yml")
    parser.add_argument("--master", help="the model you write code with")
    parser.add_argument("--provider", choices=["bedrock", "openrouter", "auto"],
                        help="where the models are called (default: .commish.yml, "
                             "then COMMISH_PROVIDER, then whichever key is set)")
    sub = parser.add_subparsers(dest="command", required=True)

    review = sub.add_parser("review", help="review a file, a snippet, or your working tree")
    review.add_argument("path", nargs="?", help="file path, or `-` to read stdin")
    review.add_argument("--lines", help="review only these lines, e.g. 40-90")
    review.add_argument("--filename", help="name for stdin input, so we know the language")
    review.add_argument("--staged", action="store_true", help="review files staged for commit")
    review.add_argument("--diff", action="store_true", help="review your uncommitted changes")
    review.add_argument("--committee", nargs="*", help="override the committee")
    review.add_argument("--format", choices=["md", "json"], default="md")
    review.add_argument("--fail-on", choices=["low", "medium", "high", "never"], default="never",
                        help="exit 1 when an issue at this severity is found")
    review.add_argument("--out", help="write to a file instead of stdout")
    review.add_argument("-q", "--quiet", action="store_true", help="no progress on stderr")
    review.set_defaults(func=cmd_review)

    doctor = sub.add_parser("doctor", help="check that a review would work right now")
    doctor.set_defaults(func=cmd_doctor)

    stats = sub.add_parser("stats", help="review metrics from the local event log")
    stats.add_argument("--log", help="path to events.jsonl (default ~/.commish/events.jsonl)")
    stats.set_defaults(func=cmd_stats)

    dash = sub.add_parser("dashboard", help="render the metrics page as self-contained HTML")
    dash.add_argument("--out", default="docs/index.html")
    dash.add_argument("--log", help="path to events.jsonl")
    dash.set_defaults(func=cmd_dashboard)

    models = sub.add_parser("models", help="list models the provider will serve")
    models.set_defaults(func=cmd_models)

    mcp = sub.add_parser("mcp", help="run as an MCP server on stdio (Claude Code, Cursor, Codex)")
    mcp.set_defaults(func=cmd_mcp)

    pr = sub.add_parser("review-pr", help="review the current pull request (GitHub Action)")
    pr.add_argument("--max-files", type=int, default=5)
    pr.add_argument("--fail-on", choices=["low", "medium", "high", "never"], default="never")
    pr.set_defaults(func=cmd_review_pr)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
