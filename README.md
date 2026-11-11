# The Commission

```
⠀⠀⠀⠀⠀⢀⢀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⢀⣠⣤⣼⣿⣿⣿⣾⣶⡤⠄⠀⠀⠀⠀⠀⠀⠀
⠀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣄⡀⠀⠀⠀⠀⠀⠀
⠘⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣉⡄⠀⠀⠀⠀
⢀⣾⢿⣿⣿⡿⠿⠿⠿⠿⢿⣿⣿⡿⣿⢇⠀⠀⠀⠀
⠀⠀⠀⠀⢨⣷⡀⠀⠀⠐⣢⣬⣿⣷⡁⣾⠀⠀⠀⠀
⢀⡠⣤⣴⣾⣿⣿⣷⣦⣿⣿⣿⣿⣿⠿⡇⠀⠀⠀⠀
⠈⠙⣿⡿⠚⠿⠟⢿⣟⣿⣿⣿⣿⣿⠉⠀⠀⠀⠀⠀
⠀⠀⣹⠵⠀⠠⠼⠯⠝⣻⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀
⠀⠀⠻⢂⡄⠒⠒⠛⣿⡿⠛⠻⠋⣼⠀⠀⠀⠀⠀⠀
⠀⠀⠠⡀⠰⠶⠿⠿⠷⠞⠀⣠⣴⠟⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠈⠂⣀⠀⠀⠀⠀⢠⠟⠉⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠘⠓⠂⠀⠐⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠐⡒⣂⣤⣤⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠸⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⠀⠀⢀⠤⠄⡀
⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⢀⡜⠠⢂⡗
⠀⠀⠀⠀⢻⣿⣿⣿⣿⣿⣿⣿⠇⠀⠀⠀⢓⠢⢬⡟
⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⢸⠍⠀⠀
⠀⠀⠀⠀⠈⣿⣿⣿⣿⣿⣿⡿⠀⠀⠀⠀⢸⠀⠀⠀
⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠈⠀⠀⠀
⠀⠀⠀⠀⠀⢹⣿⣿⣿⣿⣿⠏⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠘⣿⣿⣿⣿⡿⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠸⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⣿⣿⡏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⢻⣿⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠘⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀
```

> **He presides. He does not decide.** Your own model runs the review — and is the one
> model in the room forbidden from quietly overruling the rest.

The Commission sits on your code. Each Family is a **different model from a different
vendor**, reviewing independently, none of them taking another's word for anything.
Your own Don — the model you write code with — consolidates what they found, ranks it,
writes the fix, and talks to you.

## Why a Commission

A model reviewing code shares the blind spots of the model that wrote it: same training,
same failure modes, same confident silence in the same places. One AI reviewer is one
blind angle, which is why so few people act on one.

Models from different vendors fail differently. Run three on the same code and their
**agreement becomes a signal you can use**: three of three flagged it, look now; one of
three, probably noise.

## The rule that makes it honest

The Don consolidates, ranks, explains, and writes the fix. He may disagree with
anything. What he **may not** do is silently bury a defect that two or more Families
independently found — those surface anyway, labelled `the Commission is unanimous (3/3)
· the Don dissents`, with his objection printed beside theirs. You decide.

He is the model whose blind spots the Commission exists to cover. Give him a veto and
he will bury exactly what he cannot see, and the output will look *more* polished for
it. So the floor is enforced in code, not requested in a prompt.

## Install

```bash
pip install -e ./commission
```

Reviewers run through **AWS Bedrock** or **OpenRouter** — either way, one credential,
every vendor. Pick whichever key you have.

### OpenRouter — the short way

One key, and OpenAI, Google and xAI come with it, which Bedrock does not carry. Make a
key at [openrouter.ai/keys](https://openrouter.ai/keys), put a few dollars of credit on
the account (a key on an empty account authenticates and then refuses everything), and:

```bash
printf 'export OPENROUTER_API_KEY=sk-or-...\n' >> ~/.commish.env
chmod 600 ~/.commish.env
```

With only that key set, the Commission picks OpenRouter by itself: Claude Opus presides,
GPT, Gemini and DeepSeek sit on the Commission. With both keys set it prefers Bedrock —
choose explicitly with `provider: openrouter` in `.commish.yml`,
`COMMISH_PROVIDER=openrouter`, or `commish --provider openrouter …`. A Bedrock model id in
`.commish.yml` is translated to the same vendor's flagship on OpenRouter, so one config
serves both.

### AWS Bedrock

Generate a **Bedrock API key** (console → Bedrock → API keys) and grant it
**`AmazonBedrockFullAccess`**. The narrower default lets the key authenticate and then
refuses every model call, which reads as a broken tool rather than a missing permission;
it is the step people get wrong. Then enable the models themselves — access is **off by
default**, granted per account and per region, and separate from the key's permissions:
console → Bedrock → **Model access**. Turn on at least two vendors besides the one you
write code with.

Put the key where the tool will find it:

```bash
printf 'export AWS_BEARER_TOKEN_BEDROCK=ABSK...\nexport AWS_REGION=us-east-1\n' > ~/.commish.env
chmod 600 ~/.commish.env
```

That file is read automatically and never overrides a real environment variable. Then
see what your account will actually serve:

```bash
commish models
```

Then point [`.commish.yml`](commission/.commish.yml) at the model you write code with.
The Commission assembles itself from the other vendors.

Then check the whole thing works before trusting it with anything:

```bash
commish doctor
```

It verifies the credentials, makes one cheap call to every model you configured, and
says plainly whether a review would succeed — and warns you if fewer than two other
vendors can be reached, because agreement among models from one vendor means little.

Run it without a key and it will tell you so — at some length, and with the four steps
that fix it. Run it with a key but no model access and it will say that instead, because
those are different problems and only one of them is your fault.

## Use

```bash
commish review orders.py                    # a file
commish review orders.py --lines 40-90      # a chunk
pbpaste | commish review - --filename x.py  # a snippet
commish review --staged                     # what you are about to commit
commish review orders.py --format json      # for agents and CI
commish mcp                                 # serve to any MCP agent
commish stats                               # your own numbers
```

Exit codes: `0` clean, `1` findings at or above `--fail-on`, `2` could not run.

## Where it plugs in

The CLI is the product; everything else is a thin adapter over it — an **MCP server**
(Claude Code, Cursor, Codex), a **git pre-commit hook**, a **GitHub Action** for pull
requests. Setup for each: [`commission/integrations/`](commission/integrations/).

When an **agent** calls it, the agent *is* the Don — it wrote the code and it holds the
conversation — so that path skips the consolidation model entirely and hands the raw
findings to the caller under the same no-veto rule. One voice, one bill.

## Metrics

Every review writes one record: which models ran, what they corroborated, whether the
fix verified, what it cost. **Counts only — no source code, file paths, repository
names, or finding text.** A tool whose argument is that your code stays in your own
account does not get an exception for its own telemetry.

📊 **[Live metrics](https://teslavr.github.io/commission/)** · `COMMISH_NO_TELEMETRY=1`
turns it off entirely.

## Documentation

| | |
|---|---|
| [STRATEGY.md](STRATEGY.md) | who it is for, how it grows, how success is measured, what would kill it |
| [ARCHITECTURE.md](ARCHITECTURE.md) | the flow, the failure modes, and which ones are most likely to break it |
| [ROADMAP.md](ROADMAP.md) | what is deliberately not built, and what comes next |

## Status

Working, and verified against live models. The Commission — Meta Llama 3.3 70B, Mistral
Pixtral Large, DeepSeek R1 — found both planted defects in
[`samples/orders.py`](commission/samples/orders.py) unanimously and independently,
proposed a fix that verified, and correctly found nothing in
[`samples/clean.py`](commission/samples/clean.py). Roughly 20 seconds per file.

It reviews whole files rather than diffs, verifies fixes only for Python, and does not
yet track which fixes get merged — see [ROADMAP.md](ROADMAP.md).
