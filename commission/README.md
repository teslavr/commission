# The Commission

The Commission sits on your code. Each Family is a **different model from a different
vendor**, and none takes another's word for anything. Your own Don presides — and he is
not allowed to overrule them.

## Why a Commission

A model reviewing code shares the blind spots of the model that wrote it: same
training, same failure modes. One AI reviewer is one blind angle, which is why
nobody trusts it. Three Families that fail differently cover each other, and their
*agreement* becomes something you can act on: three out of three flagged it →
look now; one out of three → probably noise.

## The one rule that makes it honest

The Don — your own model — consolidates, ranks, explains, and writes the fix. He may
disagree with anything. What he **may not** do is silently bury a defect that two or more
Families independently found. Those surface anyway, labelled `the Commission is unanimous
(3/3) · the Don dissents`, with his objection printed beside theirs. You decide.

The historical Commission governed the Five Families: separate organisations, mutual
distrust, decisions by vote precisely because no single family could be trusted to rule
alone. That is this architecture, exactly.

Without that rule the whole thing collapses into a model marking its own
homework, which is the failure mode this product exists to avoid.

## Install

```bash
pip install -e .
```

You need AWS Bedrock: one credential, many vendors. Model access is **off by
default** — enable it per model in the Bedrock console, then check:

```bash
commish models          # what this account can actually call, in this region
```

Point `.commish.yml` at the model you write code with — that is your Don. The Commission
assembles itself from the other vendors.

## Use

```bash
commish review orders.py                    # a file
commish review orders.py --lines 40-90      # a chunk
pbpaste | commish review - --filename x.py  # a snippet
commish review --staged                     # what you are about to commit
commish review orders.py --format json      # for agents and CI
commish mcp                                 # serve to any MCP agent
```

Exit codes: `0` clean, `1` findings at or above `--fail-on`, `2` could not run.

For Claude Code / Cursor / Codex / git hooks / GitHub Actions, see
[`integrations/README.md`](integrations/README.md).

## How it fits together

```
your code
    │
    ├──► Commission  (N Families, other vendors, in parallel, no contact)
    │       each returns: findings + its own corrected file
    │
    ├──► the Don     (your model)  ── groups · judges · ranks · writes the fix
    │       cannot suppress a finding ≥ consensus_floor
    │
    ├──► verify      proposed fix must parse; optional test/lint command
    │       broken fix → not offered
    │
    └──► output      markdown for humans · JSON for agents · PR comment for teams
```

When an **agent** calls commish over MCP, the Don's step is skipped: the agent
that wrote the code is already the Don, so it gets the raw Commission findings
and the same no-veto rule, and presides itself.

## Layout

| Path | What it is |
|---|---|
| `commish/engine.py` | the only entry point; every surface calls this |
| `commish/panel.py` | the Commission, sitting in parallel |
| `commish/master.py` | the Don: consolidation, the no-veto rule, fallback clustering |
| `commish/verify.py` | a fix that does not parse is never proposed |
| `commish/providers.py` | Bedrock Converse — one shape for every vendor |
| `commish/mcp_server.py` | stdio JSON-RPC, no dependencies |
| `commish/github.py` | the only file that knows GitHub exists |

## Known limits

- Python-aware only for verification (`ast.parse`); other languages are reviewed
  but their fixes ship as `unverified`.
- Whole files or explicit chunks — not yet diff-aware, so on a large PR it
  reviews the file rather than only what changed.
- Cost and latency scale with the size of the Commission: three models per file, tens of
  seconds, cents per call. Not something to run on every save.
