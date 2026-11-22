#!/usr/bin/env python3
"""Render a crate repository's root DOCUMENTATION.md from the org template.

    repo_doc.py --repo DIR [--print] [--entry-json FILE]

The file has two halves. The header paragraph and the generated block come from
templates/REPO_DOCUMENTATION.md; `## Terms used here` and `## Recorded exceptions`
belong to the repository and are never touched here.

The registry is crates.json beside tools/, keyed by the repository name in the
directory's `origin` remote. An existing DOCUMENTATION.md keeps everything outside
the dark-inc:generated markers, so a hand-written term or exception survives.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ORG_ROOT = Path(__file__).resolve().parent.parent
CRATES_JSON = ORG_ROOT / "crates.json"
TEMPLATE = ORG_ROOT / "templates" / "REPO_DOCUMENTATION.md"

BEGIN_MARKER = "<!-- dark-inc:generated:begin -->"
END_MARKER = "<!-- dark-inc:generated:end -->"

NO_HERO = "none yet"


def die(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


def origin_repo(directory: Path) -> str:
    """The repository name in the directory's `origin` remote URL."""
    try:
        url = subprocess.run(
            ["git", "-C", str(directory), "remote", "get-url", "origin"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError as error:
        die(f"{directory} has no origin remote: {error.stderr.strip()}")
    name = url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    return name[:-4] if name.endswith(".git") else name


def load_entries() -> list[dict]:
    try:
        entries = json.loads(CRATES_JSON.read_text())
    except FileNotFoundError:
        die(f"no registry at {CRATES_JSON}")
    except json.JSONDecodeError as error:
        die(f"{CRATES_JSON} is not valid JSON: {error}")
    if not isinstance(entries, list):
        die(f"{CRATES_JSON} must hold an array of crate entries")
    return entries


def load_entry_json(entry_json: str) -> dict:
    try:
        entry = json.loads(Path(entry_json).read_text())
    except FileNotFoundError:
        die(f"no entry at {entry_json}")
    except json.JSONDecodeError as error:
        die(f"{entry_json} is not valid JSON: {error}")
    if not isinstance(entry, dict):
        die(f"{entry_json} must hold one crate entry object")
    missing = [key for key in ("repo", "part", "capture_host", "subset", "hero")
               if key not in entry]
    if missing:
        die(f"{entry_json} is missing {', '.join(missing)}")
    return entry


def find_entry(repo: str) -> dict:
    for entry in load_entries():
        if entry.get("repo") == repo:
            return entry
    die(f"{repo} is not in crates.json")


def render(template: str, entry: dict) -> str:
    hero = entry.get("hero")
    values = {
        "{repo}": entry["repo"],
        "{part}": entry["part"],
        "{hero}": hero if hero is not None else NO_HERO,
        "{capture_host}": entry["capture_host"],
        "{subset}": entry["subset"],
    }
    rendered = template
    for placeholder, value in values.items():
        rendered = rendered.replace(placeholder, value)
    leftover = sorted(set(re.findall(r"\{[a-z_]+\}", rendered)))
    if leftover:
        die(f"unreplaced placeholders: {', '.join(leftover)}")
    return rendered


def generated_block(document: str) -> str:
    """The bytes strictly between the two markers, markers excluded.

    This is the exact substring `document.split(BEGIN_MARKER)[1].split(END_MARKER)[0]`
    returns, so a caller (readme_check.py DC03) can compare it byte for byte.
    """
    if BEGIN_MARKER not in document or END_MARKER not in document:
        die(f"DOCUMENTATION.md has no {BEGIN_MARKER} / {END_MARKER} markers")
    after = document.split(BEGIN_MARKER, 1)[1]
    return after.split(END_MARKER, 1)[0]


def splice(existing: str, rendered: str) -> str:
    """Replace the generated block, keeping everything outside the markers."""
    if BEGIN_MARKER not in existing or END_MARKER not in existing:
        die(f"DOCUMENTATION.md has no {BEGIN_MARKER} / {END_MARKER} markers")
    head, rest = existing.split(BEGIN_MARKER, 1)
    tail = END_MARKER.join(rest.split(END_MARKER)[1:])
    return head + BEGIN_MARKER + generated_block(rendered) + END_MARKER + tail


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True, metavar="DIR", help="the crate repository")
    parser.add_argument("--print", action="store_true",
                        help="print the generated block; write nothing")
    parser.add_argument("--entry-json", metavar="FILE",
                        help="one crates.json-shaped entry instead of the origin lookup")
    args = parser.parse_args()

    directory = Path(args.repo).resolve()
    if not directory.is_dir():
        die(f"{directory} is not a directory")

    # --entry-json replaces the origin lookup: new_crate.py --dry-run renders a
    # document for a directory that is not a git checkout of the crate yet.
    if args.entry_json is not None:
        entry = load_entry_json(args.entry_json)
    else:
        entry = find_entry(origin_repo(directory))
    rendered = render(TEMPLATE.read_text(), entry)

    if args.print:
        sys.stdout.write(generated_block(rendered))
        return

    target = directory / "DOCUMENTATION.md"
    if not target.exists():
        target.write_text(rendered)
        print(f"wrote {target}")
        return
    existing = target.read_text()
    updated = splice(existing, rendered)
    if updated == existing:
        print(f"{target} is up to date")
        return
    target.write_text(updated)
    print(f"updated {target}")


if __name__ == "__main__":
    main()
