"""Never propose a fix we have not at least compiled. Confidently-wrong is the
failure mode that kills trust in an AI reviewer."""
from __future__ import annotations

import ast
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Verdict:
    ok: bool
    label: str  # "verified" | "unverified" | "broken"
    detail: str = ""


def _syntax_check(filename: str, code: str) -> Verdict:
    if filename.endswith(".py"):
        try:
            ast.parse(code)
        except SyntaxError as exc:
            return Verdict(False, "broken", f"proposed fix does not parse: line {exc.lineno}: {exc.msg}")
        return Verdict(True, "verified", "parses cleanly")
    return Verdict(True, "unverified", "no syntax checker for this file type")


def verify_fix(filename: str, code: str, command: str | None = None) -> Verdict:
    syntax = _syntax_check(filename, code)
    if not syntax.ok:
        return syntax
    if not command:
        return syntax

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / Path(filename).name
        target.write_text(code)
        try:
            proc = subprocess.run(
                shlex.split(command) + [str(target)],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return Verdict(True, "unverified", f"verify command did not run: {exc}")

    if proc.returncode == 0:
        return Verdict(True, "verified", f"`{command}` passed")
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-5:]
    return Verdict(False, "broken", f"`{command}` failed:\n" + "\n".join(tail))
