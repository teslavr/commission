# Known limitations and what comes next

## Not built, deliberately

**Diff-awareness.** It reviews whole files or explicit line ranges, not hunks. On a
large PR it reads the file rather than only what changed — more tokens, and occasional
findings about code the author never touched. The right fix is to send the hunk plus
enclosing scope. Half a day, and the first thing I'd do next.

**Inline suggested changes on GitHub.** The bot posts one comment with a diff, not
per-line `suggestion` blocks with the one-click accept. That anchoring — mapping a
finding to the exact position in the diff so the button applies cleanly — is the
fiddliest part of the GitHub integration and buys nothing architecturally. It is
mechanical work, and I would rather have spent the hours on the consensus logic.

**Real test-running as verification.** A proposed fix is checked for syntax, and a
verification command can be configured, but nothing runs the repository's own test
suite in a sandbox. That is the honest version of "verified" and it needs isolation I
didn't want to hand-roll under time pressure.

**Learning from outcomes.** Nothing records which proposed fixes were merged. That
signal is the north-star metric in the strategy doc *and* the obvious training loop for
per-repo tuning — which reviewers to trust, which severities to suppress. It is the
highest-value thing missing, and the next substantial piece of work.

**Cost and latency routing.** Every sit-down seats the full Commission. It should run one
cheap model on a trivial diff and the full panel only on risky ones. Easy, but it is a
tuning problem and tuning without usage data is guessing.

**Languages other than Python.** The Commission reviews anything — the model calls don't
care what language they're looking at. The gap is narrower than "only Python is
supported": verification is Python-only by default, and it's Python only because
`ast.parse` is a zero-dependency syntax check that ships with the interpreter running
the tool. Nothing stops another language from being verified the same way — there's
already an escape hatch (`verify_command` in the config) that runs any external checker
against the proposed fix in a sandboxed temp dir — but nothing is wired up out of the
box. No default `tsc --noEmit` for TypeScript, no `go vet` for Go, no `rustc
--emit=metadata` for Rust, and no per-extension dispatch to pick one automatically.
That's a day of plumbing — detect the extension, try a short list of common toolchains,
fall back to `unverified` if none is on `PATH` — not a redesign. Until then, non-Python
fixes are honestly labelled `unverified` rather than silently trusted, which was the
right call for a first release but shouldn't be mistaken for a ceiling.

**A subscription tier, instead of a self-managed AWS key.** Onboarding today means a
trip to the AWS Bedrock console: generate an API key, grant it
`AmazonBedrockFullAccess` by hand, then separately flip on model access per vendor and
per region. That is the price of "one credential, every vendor, nothing proxied" — it
avoids running a service, and it means the tool never touches anyone's request or
response. But it hands a non-AWS user AWS's own IAM and quota UX, and that is exactly
the kind of setup friction that makes a good tool look broken before it runs once. A
subscription — a hosted proxy in front of Bedrock, metered by request or token, no AWS
account required — would remove that entirely. It is not a config flag; it is a real
service to run and bill: owning uptime, rate limits shared across customers, and a
support surface that AWS currently absorbs for free. Worth building once there is
demand past the people already comfortable pasting an AWS key — not before.

**A real installer.** Getting this running today is: clone or download the repo, have
Python 3.10+ already on the machine, `pip install -e .` from inside the checkout, then
separately go generate an AWS key. Every one of those is a place a non-developer bounces
off. The cheap win is publishing to PyPI so `pip install grumpysenior` works without a
checkout at all, plus a `pipx install grumpysenior` path so it doesn't fight the
system Python — that's an afternoon, mostly packaging metadata already in
`pyproject.toml`. A single `curl | sh` script that checks for Python, installs it via
`pipx`, and drops straight into `grumpy doctor` closes the rest of the gap for
Mac/Linux; a signed, notarized binary (PyInstaller or similar) that needs no Python at
all is the real answer for someone who isn't going to open a terminal, but that's a
different order of work — build matrix, code signing, an update mechanism — and only
worth it once the AWS-key step above stops being the bigger blocker. Ship the PyPI
package first; it's the one that pays for itself immediately.

**A UI.** There is a terminal, a PR comment, and a metrics page. Nothing else is
planned: the surfaces developers already live in are the point.

## An engineering note: the weakest reviewer sets the ceiling

The first live run dropped a reviewer because Llama returned malformed JSON — it had been asked to embed a whole source file inside a JSON
string, and did not escape the newlines. I patched the parser, and the patch made it
worse: two members failed on the next run.

The real fix was to stop asking for that at all. Findings come back as small JSON
values; the corrected code comes after a delimiter, as plain text, with nothing to
escape. Consensus went from 2/3 to 3/3 and the run got twice as fast.

I am including this because the failure is the interesting part. A cross-model product
lives or dies on its weakest Family, and "make the strong model work"
is not the same problem as "make every vendor work."

## The decision everything else serves

On the one decision the product stands on: **the Don consolidates but cannot
silently overrule the Commission.** Getting that boundary right — and building the
consensus floor that enforces it rather than trusting a prompt — was worth more than
any of the above.
