"""GitHub plumbing. The engine does not know GitHub exists; this module is the
only thing that does, which is why the same engine runs from your terminal."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

API = "https://api.github.com"
MARKER = "<!-- commission -->"


class GitHubError(RuntimeError):
    pass


@dataclass
class PullRequest:
    repo: str  # "owner/name"
    number: int
    token: str


def from_environment() -> PullRequest:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise GitHubError("GITHUB_TOKEN is not set")

    repo = os.environ.get("GITHUB_REPOSITORY")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not repo or not event_path:
        raise GitHubError("not running inside a GitHub Action (no GITHUB_REPOSITORY/GITHUB_EVENT_PATH)")

    with open(event_path) as handle:
        event = json.load(handle)
    number = (event.get("pull_request") or {}).get("number")
    if not number:
        raise GitHubError("this event is not a pull request")

    return PullRequest(repo=repo, number=int(number), token=token)


def _request(pr: PullRequest, method: str, path: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(f"{API}{path}", data=data, method=method)
    request.add_header("Authorization", f"Bearer {pr.token}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        raise GitHubError(f"{method} {path} -> {exc.code}: {exc.read().decode()[:300]}") from exc
    return json.loads(payload) if payload else None


def changed_files(pr: PullRequest, extensions: tuple[str, ...] = (".py",)) -> list[str]:
    """Files touched by this PR, excluding deletions."""
    out: list[str] = []
    page = 1
    while True:
        batch = _request(pr, "GET", f"/repos/{pr.repo}/pulls/{pr.number}/files?per_page=100&page={page}")
        if not batch:
            break
        for entry in batch:
            if entry.get("status") == "removed":
                continue
            if entry["filename"].endswith(extensions):
                out.append(entry["filename"])
        if len(batch) < 100:
            break
        page += 1
    return out


def upsert_comment(pr: PullRequest, body: str) -> str:
    """One comment per PR, edited in place. Nobody wants twelve bot comments."""
    body = f"{MARKER}\n{body}"
    existing = _request(pr, "GET", f"/repos/{pr.repo}/issues/{pr.number}/comments?per_page=100") or []
    for comment in existing:
        if MARKER in (comment.get("body") or ""):
            updated = _request(
                pr, "PATCH", f"/repos/{pr.repo}/issues/comments/{comment['id']}", {"body": body}
            )
            return updated["html_url"]
    created = _request(pr, "POST", f"/repos/{pr.repo}/issues/{pr.number}/comments", {"body": body})
    return created["html_url"]
