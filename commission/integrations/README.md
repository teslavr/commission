# Wiring commish into whatever you use

The CLI is the product. Everything below is a three-line adapter on top of it.

## Any MCP-capable agent (Claude Code, Cursor, Codex, …)

One server, `commish mcp`, speaks stdio JSON-RPC. In MCP mode the calling agent
*is* the Don — commish hands back the Commission's raw findings and the agent presides
itself. One voice, no second bill.

**Claude Code** — `.mcp.json` in the repo root, or `claude mcp add`:

```json
{
  "mcpServers": {
    "commission": {
      "command": "commish",
      "args": ["mcp"],
      "env": { "AWS_REGION": "us-east-1", "AWS_PROFILE": "default" }
    }
  }
}
```

**Cursor** — `.cursor/mcp.json`, same object.
**Codex** — `~/.codex/config.toml`:

```toml
[mcp_servers.commission]
command = "commish"
args = ["mcp"]
```

Then tell the agent when to reach for it (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`):

> Before telling me a non-trivial change is finished, call `commish_review` on
> what you wrote. You are the Don for its output: group findings that
> describe the same defect, judge each against the actual code, and say plainly
> where you disagree. You may not silently drop a defect two or more Families
> raised — surface it with your objection and let me decide.

## Terminal, by hand

```bash
commish review orders.py             # a file
commish review orders.py --lines 40-90
pbpaste | commish review - --filename snippet.py
commish review --staged              # what you are about to commit
```

## Git pre-commit hook

`.git/hooks/pre-commit`, `chmod +x`:

```bash
#!/usr/bin/env bash
commish review --staged --fail-on high --quiet || {
  echo "commish found a high-severity defect. Commit with --no-verify to override."
  exit 1
}
```

## CI / GitHub Actions

See `../action.yml` and `../.github/workflows/commission.yml`. On a pull request the
built-in Don runs (no agent is present to be one), and the review is
posted as a single comment that is edited in place on every push.
