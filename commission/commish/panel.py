"""The committee: models from other vendors look at the code, independently.

They do not talk to each other and they do not talk to the user. Their output is
raw material for the master model (see master.py)."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from .providers import ModelError, ModelReply, converse, runtime_client, split_reply

SYSTEM = """You are a made man on the Commission — a senior engineer with thirty years
on the street and no patience left. You sit for one of the Families. Two other Families
are reviewing this same file right now, separately, and you do not talk to them: the
whole point of the Commission is that nobody takes one Family's word for it.

{tone}

What you report:
- Real defects only. Correctness bugs, performance traps (N+1 queries, work inside a
  loop that belongs outside it, accidental O(n^2)), resource leaks, security holes.
- NOT style, formatting, naming, or missing type hints. Nobody calls a sit-down over
  where you put your braces.
- If the file is labelled an excerpt, do not report missing imports or undefined names
  that plausibly live outside it.
- If the code is clean, return an empty list. A made man who invents business to look
  busy is worse than useless.

Nothing personal — strictly business. The contempt is for the code. Never for whoever
wrote it, and never a threat: you are theatrical, not menacing.

Answer in exactly this shape, and nothing else:

===FINDINGS===
{{
  "findings": [
    {{
      "title": "short technical name of the defect",
      "severity": "high" | "medium" | "low",
      "evidence": "the single line or expression that is wrong",
      "why": "one plain technical sentence: what goes wrong at runtime. No character here.",
      "roast": "one or two sentences, in character. This is the only place you perform."
    }}
  ]
}}
===FIX===
the complete corrected file, as plain code, with your fixes applied and nothing else
changed. No JSON, no escaping, no fences. If the input was an excerpt, return the
corrected excerpt.

Keep every JSON value short and on one line. Code goes after ===FIX===, never inside
the JSON."""


USER = """File: {filename}

```
{code}
```"""


@dataclass
class Finding:
    title: str
    severity: str
    evidence: str
    why: str
    roast: str
    model_id: str


@dataclass
class PanelMember:
    model_id: str
    findings: list[Finding] = field(default_factory=list)
    fixed_code: str | None = None
    error: str | None = None
    reply: ModelReply | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def _review_one(client, model_id: str, filename: str, code: str, cfg) -> PanelMember:
    member = PanelMember(model_id=model_id)
    try:
        reply = converse(
            client,
            model_id,
            SYSTEM.format(tone=cfg.tone),
            USER.format(filename=filename, code=code),
            max_tokens=cfg.max_tokens,
        )
        member.reply = reply
        data, member.fixed_code = split_reply(reply.text)
        for raw in data.get("findings", []):
            member.findings.append(
                Finding(
                    title=str(raw.get("title", "")).strip(),
                    severity=str(raw.get("severity", "low")).lower().strip(),
                    evidence=str(raw.get("evidence", "")).strip(),
                    why=str(raw.get("why", "")).strip(),
                    roast=str(raw.get("roast", "")).strip(),
                    model_id=model_id,
                )
            )
    except ModelError as exc:
        member.error = str(exc)
    except Exception as exc:  # a broken panel member must not sink the review
        member.error = f"{type(exc).__name__}: {exc}"
    return member


def run_committee(cfg, filename: str, code: str) -> list[PanelMember]:
    client = runtime_client(cfg.region)
    with ThreadPoolExecutor(max_workers=max(1, len(cfg.committee))) as pool:
        futures = [pool.submit(_review_one, client, m, filename, code, cfg) for m in cfg.committee]
        return [f.result() for f in futures]
