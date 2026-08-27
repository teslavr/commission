"""MCP over stdio. Hand-rolled JSON-RPC, no dependencies -- the whole point is
that this drops into Claude Code, Cursor, Codex, or anything else that speaks
MCP without dragging a package tree behind it."""
from __future__ import annotations

import json
import sys
import traceback

from .config import Config, default_committee
from .engine import review_committee_only, review_source
from .sources import from_git

PROTOCOL = "2025-06-18"

TOOLS = [
    {
        "name": "grumpy_review",
        "description": (
            "Get a second opinion on code from a committee of senior models from "
            "OTHER vendors than yours -- they do not share your blind spots. "
            "Returns their raw, independent findings for YOU to consolidate: you "
            "are the master reviewer. Call this before telling the user a "
            "non-trivial piece of code is finished, or whenever they ask for a "
            "review. The result tells you how to carry the verdict back -- as the "
            "Don, on behalf of the Commission, in the conversation's language. "
            "Pass either `code` or `path`."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "The code to review."},
                "path": {"type": "string", "description": "Path to a file to review instead."},
                "filename": {
                    "type": "string",
                    "description": "Name/extension so the committee knows the language, e.g. orders.py",
                },
                "consolidate": {
                    "type": "boolean",
                    "description": (
                        "Default false: you consolidate. Set true only if you want a "
                        "separate master model to write the review for you."
                    ),
                },
            },
        },
    },
    {
        "name": "grumpy_review_changes",
        "description": (
            "Same committee, pointed at the files you have actually changed in this "
            "working tree (uncommitted, or staged). Use before a commit or PR."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "staged": {"type": "boolean", "description": "Only files staged for commit."}
            },
        },
    },
]


def _text(payload) -> dict:
    body = payload if isinstance(payload, str) else json.dumps(payload, indent=2)
    return {"content": [{"type": "text", "text": body}]}


def _call_tool(cfg: Config, name: str, arguments: dict) -> dict:
    if name == "grumpy_review":
        code = arguments.get("code")
        filename = arguments.get("filename")
        if not code:
            path = arguments.get("path")
            if not path:
                raise ValueError("pass either `code` or `path`")
            source = __import__("grumpy.sources", fromlist=["from_file"]).from_file(path)
            code, filename = source.code, filename or source.label
        filename = filename or "snippet.py"

        if arguments.get("consolidate"):
            return _text(review_source(cfg, filename, code, surface="mcp").as_dict())
        return _text(review_committee_only(cfg, filename, code))

    if name == "grumpy_review_changes":
        sources = from_git(staged=bool(arguments.get("staged")))
        if not sources:
            return _text({"reviewed": [], "note": "no changed files to review"})
        return _text(
            [review_committee_only(cfg, s.label, s.code) for s in sources]
        )

    raise ValueError(f"unknown tool: {name}")


def _handle(cfg: Config, message: dict) -> dict | None:
    method = message.get("method")
    request_id = message.get("id")

    if method == "initialize":
        requested = (message.get("params") or {}).get("protocolVersion") or PROTOCOL
        result = {
            "protocolVersion": requested,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "grumpysenior", "version": "0.1.0"},
        }
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = message.get("params") or {}
        try:
            result = _call_tool(cfg, params.get("name", ""), params.get("arguments") or {})
        except Exception as exc:  # tool errors are results, not protocol errors
            from .preflight import access_denied_message, credentials_present, no_credentials_message

            detail = f"{type(exc).__name__}: {exc}"
            if not credentials_present():
                detail = no_credentials_message()
            elif "accessdenied" in str(exc).lower():
                detail = access_denied_message()
            result = {"content": [{"type": "text", "text": detail}], "isError": True}
    elif method and method.startswith("notifications/"):
        return None  # notifications get no reply
    elif request_id is None:
        return None
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"method not found: {method}"},
        }

    if request_id is None:
        return None
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def serve(cfg: Config) -> None:
    if cfg.master and not cfg.committee:
        cfg.committee = default_committee(cfg.master)
    print(
        f"grumpysenior MCP · committee: {', '.join(cfg.committee)} · region: {cfg.region}",
        file=sys.stderr,
        flush=True,
    )
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            response = _handle(cfg, message)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            continue
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
