#!/usr/bin/env python3
"""Check the code references in a crate's README and guide against its Rust source.

    doc_refs_check.py --repo DIR [--json OUT]

DR01 is Tan, Wagner & Treude 2023: an identifier a document names must still exist
in the code. Every inline code span that looks like a code path -- CamelCase with two
or more humps, a snake_case name, or a `::` path -- must have its last segment occur
as a whole word in some `*.rs` file of the repository.

Package and dependency names come from `cargo metadata` and are exempt, as is any
token listed one per line in the optional `docs/.doc-refs-allow`.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

TOKEN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(::[A-Za-z_][A-Za-z0-9_]*)*(\(\))?$")
INLINE_CODE_RE = re.compile(r"`(?P<code>[^`\n]+)`")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
CAMEL_HUMP_RE = re.compile(r"[A-Z][a-z0-9]*|[A-Z]+(?![a-z])")
ALLOW_FILE = Path("docs") / ".doc-refs-allow"
CRATES_JSON = HERE.parent / "crates.json"
DOC_GLOBS = ("README.md", "docs/guide/*.md", "docs/guide/**/*.md")
MAX_SEGMENT = 1


class ToolError(Exception):
    """Something the check could not measure; reported as a failure, never guessed."""


def die(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


def origin_repo(directory: Path, repo_name: str | None) -> str:
    """The repository name, from --repo-name or from the directory's origin remote.

    A directory with no remote (a scratch fixture, new_crate.py --dry-run) must be
    named outright; there is no guessing from the directory's basename.
    """
    if repo_name is not None:
        return repo_name
    try:
        url = subprocess.run(
            ["git", "-C", str(directory), "remote", "get-url", "origin"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", "") or str(error)
        die(f"{directory} has no origin remote ({str(detail).strip()}); pass --repo-name NAME")
    match = re.search(r"github\.com[:/]+(?P<owner>[^/]+)/(?P<name>[^/]+?)(?:\.git)?/?$", url)
    if match is None:
        die(f"{directory}'s origin is not a GitHub URL: {url}")
    return match.group("name")


def prose_lines(path: Path) -> list[tuple[int, str]]:
    """(line number, text) outside fenced code blocks."""
    found = []
    in_fence = False
    for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            found.append((number, line))
    return found


def is_code_reference(code: str) -> bool:
    if not TOKEN_RE.match(code):
        return False
    if "::" in code or "_" in code:
        return True
    return len(CAMEL_HUMP_RE.findall(code)) >= 2


def last_segment(code: str) -> str:
    return code.removesuffix("()").rsplit("::", 1)[-1]


def rust_tokens(directory: Path, tokens: list[str]) -> set[str]:
    """Those of `tokens` that occur as a whole word in some *.rs file, one rg each."""
    found: set[str] = set()
    for token in tokens:
        try:
            result = subprocess.run(
                ["rg", "-q", "-P", "-t", "rust", "-e", rf"(?<![\w]){re.escape(token)}(?![\w])", "."],
                cwd=str(directory), capture_output=True, text=True,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ToolError(f"rg failed: {error}") from error
        if result.returncode == 0:
            found.add(token)
        elif result.returncode > 1:
            raise ToolError(f"rg failed: {result.stderr.strip()[:200]}")
    return found


def cargo_names(directory: Path) -> set[str]:
    """Every package and dependency name in the resolved graph, from `cargo metadata`."""
    try:
        result = subprocess.run(
            ["cargo", "metadata", "--format-version", "1"],
            cwd=str(directory), capture_output=True, text=True, timeout=300,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ToolError(f"cargo metadata failed: {error}") from error
    if result.returncode != 0:
        raise ToolError(f"cargo metadata failed: {result.stderr.strip()[-300:]}")
    try:
        metadata = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ToolError(f"cargo metadata printed no JSON: {error}") from error
    names = {package["name"] for package in metadata.get("packages", [])}
    for package in metadata.get("packages", []):
        for dependency in package.get("dependencies", []):
            names.add(dependency["name"])
            names.add(dependency["name"].replace("-", "_"))
    return names


def family_names() -> set[str]:
    """The family's own crate names: package names a document may name, not code references."""
    if not CRATES_JSON.is_file():
        return set()
    try:
        entries = json.loads(CRATES_JSON.read_text())
    except json.JSONDecodeError as error:
        die(f"{CRATES_JSON} is not valid JSON: {error}")
    if not isinstance(entries, list):
        die(f"{CRATES_JSON} must hold an array of crate entries")
    return {entry["repo"] for entry in entries if isinstance(entry, dict) and "repo" in entry}


def allowed(directory: Path) -> set[str]:
    path = directory / ALLOW_FILE
    if not path.is_file():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def documents(directory: Path) -> list[Path]:
    found: list[Path] = []
    for pattern in DOC_GLOBS:
        for path in sorted(directory.glob(pattern)):
            if path.is_file() and path not in found:
                found.append(path)
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True, metavar="DIR", help="the crate repository")
    parser.add_argument("--json", metavar="OUT", help="write the checks as JSON here")
    parser.add_argument("--repo-name", metavar="NAME",
                        help="the repository name, for a directory with no origin remote")
    args = parser.parse_args()

    directory = Path(args.repo).resolve()
    if not directory.is_dir():
        die(f"{directory} is not a directory")

    repo = origin_repo(directory, args.repo_name)

    # (file, line, code) for every candidate reference, deduplicated per location.
    references: list[tuple[str, int, str]] = []
    for path in documents(directory):
        for number, line in prose_lines(path):
            for match in INLINE_CODE_RE.finditer(line):
                code = match.group("code").strip()
                if is_code_reference(code):
                    references.append((str(path.relative_to(directory)), number, code))

    checks: list[dict] = []
    failures = 0
    try:
        exempt = cargo_names(directory) | allowed(directory) | family_names()
        tokens = sorted({last_segment(code) for _, _, code in references if last_segment(code) not in exempt})
        present = rust_tokens(directory, tokens) if tokens else set()
    except ToolError as error:
        failures += 1
        checks.append({"id": "DR01", "ok": False, "file": "README.md", "line": 0, "message": str(error)})
        print(f"DR01 FAIL README.md:0 {error}")
    else:
        for file, line, code in references:
            segment = last_segment(code)
            if segment in exempt or segment in present:
                continue
            failures += 1
            checks.append({"id": "DR01", "ok": False, "file": file, "line": line,
                           "message": f"`{code}`: `{segment}` occurs in no *.rs file"})
            print(f"DR01 FAIL {file}:{line} `{code}`: `{segment}` occurs in no *.rs file")
        if not failures:
            checks.append({"id": "DR01", "ok": True, "file": None, "line": None, "message": ""})
        print(f"DR01 checked {len(references)} references, {len(tokens)} distinct tokens", file=sys.stderr)

    if args.json:
        Path(args.json).write_text(json.dumps({"repo": repo, "checks": checks}, indent=2) + "\n")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
