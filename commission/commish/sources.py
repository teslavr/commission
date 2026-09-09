"""Where code comes from. A reviewer you can only point at whole files is a
reviewer you will not call at 4pm on a Friday."""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Source:
    label: str  # what the models are told they are looking at
    code: str
    path: Path | None = None
    excerpt: bool = False


def _slice(code: str, lines: str) -> tuple[str, str]:
    """`40-90` or `40` -> the slice plus a human label."""
    if "-" in lines:
        start_s, end_s = lines.split("-", 1)
        start, end = int(start_s), int(end_s)
    else:
        start = end = int(lines)
    rows = code.splitlines()
    start = max(1, start)
    end = min(len(rows), end)
    return "\n".join(rows[start - 1 : end]) + "\n", f"lines {start}-{end} of {len(rows)}"


def from_file(path_str: str, lines: str | None = None) -> Source:
    path = Path(path_str)
    if not path.is_file():
        raise FileNotFoundError(path_str)
    code = path.read_text()
    if lines:
        sliced, span = _slice(code, lines)
        return Source(label=f"{path.name} ({span}, excerpt)", code=sliced, path=path, excerpt=True)
    return Source(label=path.name, code=code, path=path)


def from_stdin(filename: str | None) -> Source:
    code = sys.stdin.read()
    if not code.strip():
        raise ValueError("nothing on stdin")
    name = filename or "snippet.py"
    return Source(label=f"{name} (pasted snippet, excerpt)", code=code, excerpt=True)


def _git(*args: str) -> str:
    proc = subprocess.run(["git", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git failed")
    return proc.stdout


def from_git(staged: bool = False, extensions: tuple[str, ...] = (".py",)) -> list[Source]:
    """Files you are actually working on right now."""
    args = ["diff", "--name-only", "--diff-filter=d"]
    if staged:
        args.append("--cached")
    names = [n for n in _git(*args).splitlines() if n.strip().endswith(extensions)]
    if not names:
        # Nothing uncommitted -- fall back to what the last commit touched.
        names = [
            n
            for n in _git("diff", "--name-only", "--diff-filter=d", "HEAD~1", "HEAD").splitlines()
            if n.strip().endswith(extensions)
        ]
    out = []
    for name in names:
        path = Path(name)
        if path.is_file():
            out.append(Source(label=path.name, code=path.read_text(), path=path))
    return out
