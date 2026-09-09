# Product strategy

**The Commission sits on your code: five Families, five different models, five different
vendors, none of whom take each other's word for anything. Your own Don presides — and
he is not allowed to overrule them.**

## Why it exists

AI writes most of the code now. The bottleneck moved from producing code to judging it.

But the obvious fix — point a model at the diff — has a defect people feel before they
can name it: **a model reviewing code shares the blind spots of the model that wrote
it.** Same training, same failure modes, same confident silence in the same places. One
AI reviewer is one blind angle. So teams read the first few reviews, notice it flags
what they already knew and misses what they didn't, and quietly turn it off.

Everyone is shipping the single-reviewer version. The interesting product is the one
that fixes the blind spot rather than restating it.

## The wedge

Models from different vendors fail differently. Sit three of them down on the same code
and **their agreement becomes a signal you can act on**: three of three flagged it, look
now; one of three, probably noise. That is not a feature you bolt on later — it is the
only thing here that a competitor cannot copy by changing a prompt.

Swap test: *"an AI bot that roasts your code"* describes six products shipping this
quarter. *"reviewers who don't share your model's blind spots, and a confidence number
that comes from their disagreement"* describes one.

The roast is the distribution. Funny, screenshot-able, team-visible — that is how it
lands in a repo. The Commission is the product. Confusing the two is how this becomes a
novelty that gets uninstalled in week two.

**The costume is load-bearing.** The historical Commission governed the Five Families:
separate organisations, mutual distrust, decisions by vote precisely because no single
family could be trusted to rule alone. That is the architecture, exactly — and the rule
below is a plot point rather than a policy document. It lets me explain the mechanism in
one sentence to someone who has never thought about model blind spots. It also fixes a
tone problem: "grumpy" slides into personal abuse, while a wiseguy is theatrical by
nature. He aims at the code, stays funny, and never has to be cruel. *Nothing personal,
strictly business* is the joke and the guardrail in the same line.

## The decision I'd defend hardest

If the Don — your own model — can overrule the Commission, the whole thing collapses. He
is the model whose blind spots the Commission exists to cover; give him a veto and he
will bury exactly what he cannot see, and the output will look *more* polished for it.

So: **the Don consolidates, ranks, explains, and writes the fix. He may disagree with
anything. He may not silently drop a defect that two or more Families independently
found.** Those surface anyway, labelled `the Commission is unanimous (3/3) · the Don
dissents`, with his objection printed beside theirs. A human decides.

This is the difference between oversight and a name to attach to the failure. It costs
us a cleaner-looking review, and it is the reason the review is worth reading.

## Who it's for

Small-to-mid teams already writing most of their code with AI, who have noticed they
don't trust a single AI to review it. They feel the problem before they can name it,
which makes the pitch short.

**Not for:** solo hobbyists with no review step at all, and — until a local-model
deployment path exists — teams who cannot send source code to a third party.

## Form factor: not an IDE plugin, not only a PR bot

The obvious places to put this are an IDE extension or a pull-request bot. Both are
useful, and both are the wrong unit to build first.

The product is a reasoning loop; the form factor is a distribution question. So the
loop ships as **a CLI with an honest contract** — a file, a chunk, a snippet on stdin,
or your staged changes; markdown for humans, JSON for machines, meaningful exit codes —
and everything else is a thin adapter over it: an MCP server (which is how it reaches
Claude Code, Cursor and Codex at once), a git hook, a GitHub Action.

That choice pays for itself immediately. When an **agent** calls it, the agent that
wrote the code is already the master — so it gets the Commission's raw findings and the
same no-veto rule, and consolidates them itself. No second model, no second bill, no
second voice arguing with the first. The architecture the product needed and the
integration the user needed turned out to be the same thing.

## How it grows

Bottom-up, one developer at a time: `pip install`, point it at a file, see whether the
Commission catches something you missed. If it does, it goes in the repo; if it doesn't,
nothing was lost. The roast is what makes the good catches get pasted into team chat.

The paid unit is the team, not the seat: the PR bot, shared config, the audit trail of
what was proposed and what was merged.

## How we measure success

**North star: proposed fixes that get merged.** Not reviews delivered, not issues
found — trust made countable.

Supporting: re-invocation rate (does anyone call it a second week?), the ratio of
contested findings that turn out to be real (does the no-veto rule earn its keep, or
is it just noise?), and time from review to action.

**These are instrumented, not aspirational.** Every sit-down writes one record, and
`commish stats` and the published page compute exactly the numbers above — including the
one that decides whether the product has a floor at all: how often independent Families
corroborate each other. A kill criterion you cannot compute is a wish.

**And the records carry no content.** Not the code, not file paths, not repository
names, not the text of a finding — only shape: which Families sat, what they agreed on,
what it cost, whether the fix verified. A product whose enterprise argument is "your
code never leaves your account" does not get an exception for its own telemetry. That
constraint was designed into the schema before the first chart existed, which is why
the analytics page can be public.

One metric earns its place beyond the doc: **per-Family yield.** Findings per sitting,
and drop-out rate, per vendor. It answers an operational question nobody else has to
ask — *which Families still deserve a seat* — and it is the beginning of routing.

## Validating it before writing complex code

The expensive assumption is not "will three Families find bugs" — they will. It is
**"will three vendors describe the same bug similarly enough that agreement can be
computed at all?"** If they don't cluster, the confidence number is fiction and the
product has no floor.

That is testable in an afternoon, without a product: run the Commission by hand over
twenty real diffs and count how often independent reviewers land on the same defect.
Then a concierge round — post the consolidated review as an ordinary comment on real
PRs, signed as a human, and see whether the fixes get merged.

## What kills it

- **Agreement doesn't cluster.** The Families never converge, confidence is unfalsifiable
  → the wedge was imaginary. Kill it; do not paper over it with a prettier UI.
- **Fixes don't get merged.** Below roughly a fifth, over enough PRs, the reviews are
  entertainment. Kill or pivot to detection-only.
- **Novelty-only usage.** No second week → the roast was the whole product, and the
  roast is not a product.
- **Contested findings are consistently wrong.** The safety property becomes noise, the
  Don's veto starts looking correct, and the honest move is to admit it.

## What I believe is critical

Two things, and they are the same thing seen twice. The differentiator is
**cross-model trust, not the roast.** And trust is a property of what the system is not
allowed to do — quietly agree with itself — far more than of what it produces.
