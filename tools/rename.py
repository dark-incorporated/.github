#!/usr/bin/env python3
"""Rename one crate repository from the old family names to Dark Inc.'s names.

Run from anywhere:  python3 .github/tools/rename.py --repo DIR [--check]

`--check` prints every forbidden name and changes nothing; it exits 1 when there are
any, 0 when there are none. Without it, the paths are moved with `git mv`, then every
tracked text file is rewritten. The map lives in `.github/names.json`, which is also
read by the check tools and by the book's glossary generator, so the map has one home.

Order, and why:

1. **Paths first.** A moved file keeps its history only if the move happens before its
   contents change, and a path that collides with an existing one is reported rather
   than guessed (`COLLISION`, exit 3, nothing changed).
2. **Old basenames** (`cauldron.md` → `dark-factory.md`) so a link keeps pointing at the
   file that now exists.
3. **Identifiers and prose, longest first, with word boundaries.** `bevy_cauldron_mcp`
   is consumed before `bevy_cauldron` and before `cauldron`, because a shorter rule that
   ran first would leave a name no rule predicts. Identifiers (a token embedded in a
   longer name, path or namespace: `bevy_cauldron`, `cauldron::startup`, `cauldron.log`)
   get the underscore form; prose gets the display name.
4. **Post fixes** for the grammar the replacements leave behind (`the the Dark Factory`,
   `Dark Inc..`, a sentence that now starts mid-name).

Every step is idempotent: after one pass no rule matches again, so a second run reports
no edits.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

NAMES_PATH = Path(__file__).resolve().parent.parent / "names.json"

# A file over this size is a capture, a lock file or an asset tree: too big to rewrite
# safely for what it gains, and the plan excludes it.
MAX_BYTES = 4 * 1024 * 1024
SKIP_BASENAMES = frozenset({"Cargo.lock"})
SKIP_SUFFIXES = (".lock", ".plist.in")
SKIP_DIR_PARTS = frozenset({"target"})
# Art that must keep reproducing the images it made keeps the names it was written with.
SKIP_DIR_TAILS = ("art/archive", ".github/art/archive")
# The dictionary keeps the old names on purpose (`formerly`, `forbidden`), the book's glossary is
# generated from it, and this script's own comments quote old names as examples.
SKIP_PATHS = frozenset({"names.json", "src/glossary.md", "tools/rename.py"})

# Characters that join a token into a longer name: `bevy_cauldron`, `cauldron::startup`,
# `grimoire-ui`, `cauldron.log`, `docs/guide/cauldron`.
JOINERS = frozenset(":/.-")

EXIT_OK = 0
EXIT_FORBIDDEN = 1
EXIT_COLLISION = 3


def load_names() -> dict:
    """The one rename map, as written in `.github/names.json`."""
    with NAMES_PATH.open(encoding="utf-8") as handle:
        names = json.load(handle)
    for key in ("canonical", "paths", "identifiers", "text", "post", "labels", "forbidden"):
        if key not in names:
            raise SystemExit(f"{NAMES_PATH}: missing key {key!r}")
    return names


def forbidden_patterns(names: dict | None = None) -> list[re.Pattern[str]]:
    return [re.compile(pattern) for pattern in (names or load_names())["forbidden"]]


def forbidden_hits(text: str) -> list[tuple[int, str]]:
    """Every forbidden name in `text`, as (1-based line number, matched text)."""
    hits: list[tuple[int, str]] = []
    for pattern in forbidden_patterns():
        for match in pattern.finditer(text):
            hits.append((text.count("\n", 0, match.start()) + 1, match.group(0)))
    return sorted(hits, key=lambda hit: (hit[0], hit[1]))


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(("git", "-C", str(repo), *args), capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed in {repo}: {done.stderr.strip()}")
    return done.stdout


def tracked_files(repo: Path) -> list[str]:
    return sorted(path for path in git(repo, "ls-files", "-z").split("\0") if path)


def is_word(character: str) -> bool:
    return character.isalnum() or character == "_"


def embedded(text: str, start: int, end: int) -> bool:
    """Is the token at `text[start:end]` part of a longer name, path or namespace?

    A run left or right of the token may cross `JOINERS` (`.`, `/`, `:`, `-`); reaching a
    word character means the token is embedded, which is what makes it an identifier
    rather than a word of prose. `cauldron.` at the end of a sentence is prose;
    `cauldron.md` and `bevy_cauldron` are not.
    """
    index = start - 1
    while index >= 0 and text[index] in JOINERS:
        index -= 1
    if index >= 0 and is_word(text[index]):
        return True
    index = end
    while index < len(text) and text[index] in JOINERS:
        index += 1
    return index < len(text) and is_word(text[index])


def substitute_identifier(text: str, old: str, new: str) -> str:
    out: list[str] = []
    cursor = 0
    for match in re.finditer(re.escape(old), text):
        if not embedded(text, match.start(), match.end()):
            continue
        out.append(text[cursor : match.start()])
        out.append(new)
        cursor = match.end()
    out.append(text[cursor:])
    return "".join(out)


def substitute_text(text: str, old: str, new: str) -> str:
    pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(old)}(?![A-Za-z0-9_])")
    return pattern.sub(lambda _match: new, text)


def ordered_rules(names: dict) -> list[tuple[str, str, bool]]:
    """(old, new, is_identifier) longest first, so a longer name is never eaten by a
    shorter one. Identifiers and prose entries are merged: `bevy_cauldron_mcp` (prose
    entry, 17 characters) must run before `cauldron` (identifier entry, 8)."""
    rules = [(old, new, True) for old, new in names["identifiers"].items()]
    rules += [(old, new, False) for old, new in names["text"]]
    rules.sort(key=lambda rule: -len(rule[0]))
    return rules


def rewrite(text: str, names: dict) -> str:
    for old, new, is_identifier in ordered_rules(names):
        if is_identifier:
            text = substitute_identifier(text, old, new)
        else:
            text = substitute_text(text, old, new)
    for pattern, replacement in names["post"]:
        text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
    return text


def path_after(path: str, names: dict) -> str:
    """The path's new name: the ordered path-segment renames first, then the identifier
    form for a token embedded in a longer file name (`bevy_grimoire-demo.mp4` →
    `bevy_dark_factory-demo.mp4`). A path is the one place a name cannot be left behind:
    the forbidden check reads it, so it would fail forever."""
    for old, new in names["paths"]:
        pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(old)}(?![A-Za-z0-9_])")
        path = pattern.sub(lambda _match: new, path)
    for old, new in names["identifiers"].items():
        path = substitute_identifier(path, old, new)
    return path


def planned_moves(repo: Path, paths: list[str], names: dict) -> list[tuple[str, str]]:
    """Every (old, new) the path rules ask for, with a collision reported rather than
    guessed. A collision is two sources asking for one target, or a target that already
    exists on disk (a tracked file, or an untracked one this run must not overwrite)."""
    moves: list[tuple[str, str]] = []
    claimed_by: dict[str, str] = {}
    track = set(paths)
    for path in paths:
        if skipped(path):
            continue
        target = path_after(path, names)
        if target == path:
            continue
        if target in claimed_by:
            print(f"COLLISION {path} -> {target}", file=sys.stderr)
            print(f"COLLISION {claimed_by[target]} -> {target}", file=sys.stderr)
            raise SystemExit(EXIT_COLLISION)
        if target in track or (repo / target).exists():
            print(f"COLLISION {path} -> {target}", file=sys.stderr)
            print(f"COLLISION target {target} already exists", file=sys.stderr)
            raise SystemExit(EXIT_COLLISION)
        claimed_by[target] = path
        moves.append((path, target))
    return moves


def skipped(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    if path in SKIP_PATHS or name in SKIP_BASENAMES or name.endswith(SKIP_SUFFIXES):
        return True
    parts = path.split("/")
    if any(part in SKIP_DIR_PARTS for part in parts[:-1]):
        return True
    directory = "/".join(parts[:-1])
    return any(
        directory == skip or directory.startswith(skip + "/") or ("/" + skip + "/") in ("/" + directory + "/")
        for skip in SKIP_DIR_TAILS
    )


def read_text(repo: Path, path: str) -> str | None:
    """The file's text, or None when it is not text we rewrite: undecodable, oversized,
    or outside the tracked set."""
    full = repo / path
    try:
        if full.stat().st_size > MAX_BYTES:
            return None
        data = full.read_bytes()
    except FileNotFoundError:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def write_text(repo: Path, path: str, text: str) -> None:
    (repo / path).write_text(text, encoding="utf-8", newline="")


def prune_empty_dirs(repo: Path, moved: list[str]) -> None:
    """`git` tracks no directories, so a moved-out directory leaves an empty one behind.
    Remove only the directories this run emptied, and only up to the repository root."""
    for old in moved:
        parent = (repo / old).parent
        while parent != repo and repo in parent.parents:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent


def check(repo: Path, names: dict, shown: str) -> int:
    total = 0
    counts = {pattern: 0 for pattern in names["forbidden"]}
    for path in tracked_files(repo):
        if skipped(path):
            continue
        for pattern in names["forbidden"]:
            if re.search(pattern, path):
                for match in re.finditer(pattern, path):
                    print(f"FORBIDDEN {shown}/{path}:1: {match.group(0)}")
                    total += 1
                    counts[pattern] += 1
        text = read_text(repo, path)
        if text is None:
            continue
        for line, hit in forbidden_hits(text):
            print(f"FORBIDDEN {shown}/{path}:{line}: {hit}")
            total += 1
        for pattern in names["forbidden"]:
            counts[pattern] += len(re.findall(pattern, text))
    for pattern, count in counts.items():
        print(f"COUNT {pattern}: {count}")
    return EXIT_FORBIDDEN if total else EXIT_OK


def rename(repo: Path, names: dict, shown: str) -> int:
    moves = planned_moves(repo, tracked_files(repo), names)
    for old, new in moves:
        (repo / new).parent.mkdir(parents=True, exist_ok=True)
    for old, new in moves:
        git(repo, "mv", "--", old, new)
        print(f"RENAME {shown}/{old} -> {shown}/{new}")
    prune_empty_dirs(repo, [old for old, _new in moves])

    # Every old basename is rewritten in the text, so a link to a moved page still points
    # at the page that now exists. Longest basename first, for the same reason as above.
    renames = sorted(
        {(old.rsplit("/", 1)[-1], new.rsplit("/", 1)[-1]) for old, new in moves},
        key=lambda pair: -len(pair[0]),
    )

    edited = 0
    for path in tracked_files(repo):
        if skipped(path):
            continue
        text = read_text(repo, path)
        if text is None:
            continue
        updated = text
        for old_name, new_name in renames:
            if old_name != new_name:
                updated = updated.replace(old_name, new_name)
        updated = rewrite(updated, names)
        if updated != text:
            write_text(repo, path, updated)
            print(f"EDIT {shown}/{path}")
            edited += 1
    print(f"RENAMED {len(moves)} paths, EDITED {edited} files")
    return EXIT_OK


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True, type=Path, help="the repository to rename")
    parser.add_argument("--check", action="store_true", help="print forbidden names and change nothing")
    args = parser.parse_args()

    repo = args.repo.resolve()
    if not (repo / ".git").exists():
        raise SystemExit(f"{args.repo} is not a git repository")
    names = load_names()
    shown = str(args.repo).rstrip("/")
    if args.check:
        return check(repo, names, shown)
    return rename(repo, names, shown)


if __name__ == "__main__":
    sys.exit(main())
