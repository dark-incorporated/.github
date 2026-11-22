#!/usr/bin/env python3
"""Regenerate the family table in profile/README.md from crates.json.

    profile_table.py [--check]

Rewrites only the text between <!-- family:begin --> and <!-- family:end -->.
Groups by `part`, printing the part name in the Part column on the first row of
each group, and taking group order from each part's first appearance in
crates.json.

Published means `cargo search --limit 1 <package>` reports the package (the
answer is cached for a week under ~/.cache/dark-inc-docs/published.json).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ORG_ROOT = Path(__file__).resolve().parent.parent
CRATES_JSON = ORG_ROOT / "crates.json"
PROFILE = ORG_ROOT / "profile" / "README.md"

BEGIN_MARKER = "<!-- family:begin -->"
END_MARKER = "<!-- family:end -->"

GH_REPO = "https://github.com/dark-incorporated"
BOOK_CRATE = "https://dark-incorporated.github.io/crates"
CRATES_IO_BADGE = "https://img.shields.io/crates/v/{package}.svg"
CRATES_IO = "https://crates.io/crates/{package}"
DOCS_RS = "https://docs.rs/{package}"

# A registry answer does not change within a week, and `cargo search` is a
# network call made once per package.
CACHE_PATH = Path.home() / ".cache" / "dark-inc-docs" / "published.json"
CACHE_TTL_S = 7 * 24 * 60 * 60

# Extra packages a repo ships that share its row (the family lists both crates).
EXTRA_PACKAGES = {"isomesh": ["bevy_isomesh"]}

TABLE_HEADER = "|Part|Crate|What it does|Latest|Docs|"
TABLE_RULE = "|---|---|---|---|---|"


def die(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


def load_cache() -> dict:
    try:
        data = json.loads(CACHE_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    now = time.time()
    return {name: item for name, item in data.items()
            if now - item.get("at", 0) < CACHE_TTL_S}


def save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n")


def is_published(package: str, cache: dict) -> bool:
    if package in cache:
        return bool(cache[package]["published"])
    try:
        result = subprocess.run(
            ["cargo", "search", "--limit", "1", package],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        die("cargo is not on PATH, so published state cannot be measured")
    if result.returncode != 0:
        die(f"cargo search {package} failed: {result.stderr.strip()}")
    first_line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    published = first_line.startswith(f"{package} =")
    cache[package] = {"published": published, "at": time.time()}
    return published


def latest_cell(packages: list[str], cache: dict) -> str:
    badges = [f"[![crates.io]({CRATES_IO_BADGE.format(package=p)})]({CRATES_IO.format(package=p)})"
              for p in packages if is_published(p, cache)]
    return " ".join(badges) if badges else "git only"


def docs_cell(repo: str, packages: list[str], cache: dict) -> str:
    book = f"[book]({BOOK_CRATE}/{repo}/)"
    for package in reversed(packages):
        if is_published(package, cache):
            return f"[docs.rs]({DOCS_RS.format(package=package)}) · {book}"
    return book


def cell(text: str) -> str:
    """A table cell: one line, and `|` cannot escape the column."""
    return text.replace("\n", " ").replace("|", "\\|").strip()


def grouped(entries: list[dict]) -> list[tuple[str, list[dict]]]:
    order: list[str] = []
    members: dict[str, list[dict]] = {}
    for entry in entries:
        part = entry["part"]
        if part not in members:
            order.append(part)
            members[part] = []
        members[part].append(entry)
    return [(part, members[part]) for part in order]


def render_table(entries: list[dict], cache: dict) -> str:
    lines = [TABLE_HEADER, TABLE_RULE]
    for part, members in grouped(entries):
        for index, entry in enumerate(members):
            repo = entry["repo"]
            packages = [repo, *EXTRA_PACKAGES.get(repo, [])]
            part_cell = f"**{part}**" if index == 0 else ""
            lines.append(
                f"|{part_cell}"
                f"|[{repo}]({GH_REPO}/{repo})"
                f"|{cell(entry['pitch'])}"
                f"|{latest_cell(packages, cache)}"
                f"|{docs_cell(repo, packages, cache)}|"
            )
    return "\n".join(lines) + "\n"


def splice(document: str, table: str) -> str:
    if BEGIN_MARKER not in document or END_MARKER not in document:
        die(f"{PROFILE} has no {BEGIN_MARKER} / {END_MARKER} markers")
    head, rest = document.split(BEGIN_MARKER, 1)
    tail = END_MARKER.join(rest.split(END_MARKER)[1:])
    return f"{head}{BEGIN_MARKER}\n{table}{END_MARKER}{tail}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if the table is stale; write nothing")
    args = parser.parse_args()

    try:
        entries = json.loads(CRATES_JSON.read_text())
    except FileNotFoundError:
        die(f"no registry at {CRATES_JSON}")
    except json.JSONDecodeError as error:
        die(f"{CRATES_JSON} is not valid JSON: {error}")
    if not isinstance(entries, list) or not entries:
        die(f"{CRATES_JSON} must hold a non-empty array of crate entries")

    cache = load_cache()
    table = render_table(entries, cache)
    save_cache(cache)

    document = PROFILE.read_text()
    updated = splice(document, table)
    if args.check:
        if updated != document:
            print(f"{PROFILE} is stale; run profile_table.py", file=sys.stderr)
            sys.exit(1)
        return
    if updated == document:
        print(f"{PROFILE} is up to date")
        return
    PROFILE.write_text(updated)
    print(f"updated {PROFILE}")


if __name__ == "__main__":
    main()
