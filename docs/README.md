# Metrics

`index.html` is the metrics page, served by GitHub Pages. It is generated — do not edit
it by hand:

```bash
commish dashboard --log docs/events.jsonl --out docs/index.html
```

`events.jsonl` is the review event log: one record per review, containing counts only —
an anonymous install id, which models ran, how many findings were corroborated, whether
the proposed fix verified, and how long the review took. No source code, file paths,
repository names, or finding text is recorded.

That constraint is what makes the page publishable. It was designed into the schema
before the first chart existed rather than added afterwards: a tool whose argument is
that source code stays inside the customer's own account cannot make an exception for
its own telemetry.

Local telemetry writes to `~/.commish/` and is disabled with `COMMISH_NO_TELEMETRY=1`.
