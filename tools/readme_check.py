#!/usr/bin/env python3
"""Check a crate repository's README and guidance file against Dark Inc.'s guide.

    readme_check.py --repo DIR [--json OUT] [--entry-json FILE]

RC01-RC21 measure README.md; DC01-DC05 measure the root DOCUMENTATION.md and the
agent files. Every failure prints as `<ID> FAIL <file>:<line> <message>` and the
script exits 1 when there is one.

The repository is named by its `origin` remote because that is what crates.json
keys on; `--entry-json` supplies one crates.json-shaped object instead, for a
directory that has no remote yet (new_crate.py --dry-run).

RC04 decides "published" with `cargo search --limit 1 <repo>`: the repository's
own name is the crate a reader installs, so that is the name searched. RC06 reads
the root package's version with `cargo metadata --no-deps`.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ORG = "dark-incorporated"
ORG_URL = f"https://github.com/{ORG}"
RAW_URL = f"https://raw.githubusercontent.com/{ORG}"
BOOK_CRATE_URL = "https://dark-incorporated.github.io/crates"
DOC_GUIDE_URL = f"{ORG_URL}/.github/blob/main/DOCUMENTATION.md"
STYLE_GUIDE_URL = f"{ORG_URL}/.github/blob/main/STYLE.md"
CONTRIBUTING_URL = f"{ORG_URL}/.github/blob/main/CONTRIBUTING.md"

HERE = Path(__file__).resolve().parent
CRATES_JSON = HERE.parent / "crates.json"
REPO_DOC = HERE / "repo_doc.py"
RENAME = HERE / "rename.py"

BEGIN_MARKER = "<!-- dark-inc:generated:begin -->"
END_MARKER = "<!-- dark-inc:generated:end -->"

MAX_README_LINES = 250
MAX_DOC_LINES = 60
MAX_PITCH_WORDS = 40
MAX_QUICKSTART_RUST_LINES = 20
MAX_EXTRA_H2 = 2
MIN_BULLETS = 3
MAX_BULLETS = 7
MAX_SECTION_IMAGES = 4
MIN_CAPTION_ALT_WORDS = 5
MAX_MEDIA_BYTES = 4 * 1024 * 1024
MAX_GIF_WIDTH_PX = 960
BANNER_WINDOW_LINES = 3

BANNER = (
    "> ⚠️ **Vibe Coded.** Written by AI agents working from a human's direction, covered by tests "
    "rather than a line-by-line human review. Read the code before you rely on it for something you "
    "care about."
)

README_H2 = [
    "Quick start",
    "Try it",
    "What you can do",
    "Part of Dark Inc.",
    "Bevy compatibility",
    "Learn more",
    "Who and licence",
]

DOC_H2 = ["This repository", "Check it locally", "Terms used here", "Recorded exceptions"]

DC05_LINE = (
    "Documentation follows ./DOCUMENTATION.md, which defers to Dark Inc.'s DOCUMENTATION.md and "
    "STYLE.md; a feature is not done until its README line and, if it is visible, its GIF exist."
)
OLD_GUIDE_LINK = re.compile(r"follow https://github\.com/.*/DOCUMENTATION\.md")

STATUS_RE = re.compile(r"\*\*Status:\*\* (experimental|usable) · Bevy \d+\.\d+( · MSRV [\d.]+)?")
IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\(\s*(?P<url>[^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
LINK_RE = re.compile(r"(?<!!)\[(?P<text>[^\]]*)\]\(\s*(?P<url>[^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
IMG_TAG_RE = re.compile(r"<img\s[^>]*?src=\"(?P<url>[^\"]+)\"", re.IGNORECASE)
STILL_SUFFIXES = (".png", ".jpg", ".jpeg", ".svg")
REPO_PATH_URL_RE = re.compile(
    rf"^https://raw\.githubusercontent\.com/{ORG}/(?P<repo>[^/]+)/(?:main|[0-9a-f]{{7,40}})/(?P<path>.+)$"
)
REPO_BLOB_URL_RE = re.compile(r"^https://github\.com/(?P<org>[^/]+)/(?P<repo>[^/]+)/")

RC_IDS = [f"RC{number:02d}" for number in range(1, 22)]
DC_IDS = [f"DC{number:02d}" for number in range(1, 6)]


class ToolError(Exception):
    """Something the check could not measure, reported as a failure, never guessed."""


# --------------------------------------------------------------------------- registry


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
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", "") or str(error)
        die(f"{directory} has no origin remote: {str(detail).strip()}")
    match = re.search(r"github\.com[:/]+(?P<owner>[^/]+)/(?P<name>[^/]+?)(?:\.git)?/?$", url)
    if match is None:
        die(f"{directory}'s origin is not a GitHub URL: {url}")
    return match.group("name")


def find_entry(directory: Path, entry_json: str | None) -> dict:
    """The crates.json entry for this directory.

    `--entry-json` names the repository outright, so a directory that has no origin
    remote yet (new_crate.py --dry-run, which `git init`s a scratch copy) still
    resolves. Otherwise the origin remote's repository name is the key.
    """
    if entry_json is not None:
        try:
            entry = json.loads(Path(entry_json).read_text())
        except FileNotFoundError:
            die(f"no entry at {entry_json}")
        except json.JSONDecodeError as error:
            die(f"{entry_json} is not valid JSON: {error}")
        if not isinstance(entry, dict):
            die(f"{entry_json} must hold one crate entry object")
        if not isinstance(entry.get("repo"), str) or not entry["repo"]:
            die(f"{entry_json} has no `repo` name")
        return entry
    repo = origin_repo(directory)
    try:
        entries = json.loads(CRATES_JSON.read_text())
    except FileNotFoundError:
        die(f"no registry at {CRATES_JSON}")
    except json.JSONDecodeError as error:
        die(f"{CRATES_JSON} is not valid JSON: {error}")
    if not isinstance(entries, list):
        die(f"{CRATES_JSON} must hold an array of crate entries")
    for entry in entries:
        if entry.get("repo") == repo:
            return entry
    die(f"{repo} is not in crates.json")


# --------------------------------------------------------------------------- markdown


def prose_lines(lines: list[str]):
    """(line number, text) for every line outside a fenced code block."""
    in_fence = False
    for number, line in enumerate(lines, 1):
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield number, line


def h2_sections(lines: list[str]) -> list[dict]:
    """Every H2 outside code fences, with every line under it (code included)."""
    sections: list[dict] = []
    in_fence = False
    for number, line in enumerate(lines, 1):
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
            if sections:
                sections[-1]["body"].append((number, line))
            continue
        if not in_fence:
            match = re.match(r"^##\s+(.+?)\s*$", line)
            if match:
                sections.append({"title": match.group(1), "line": number, "body": []})
                continue
        if sections:
            sections[-1]["body"].append((number, line))
    return sections


def section(sections: list[dict], title: str) -> dict | None:
    for item in sections:
        if item["title"] == title:
            return item
    return None


def prose_body(item: dict) -> list[tuple[int, str]]:
    """A section's lines with its fenced code left out."""
    body = []
    in_fence = False
    for number, line in item["body"]:
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
            continue
        if not in_fence:
            body.append((number, line))
    return body


def section_text(item: dict, include_code: bool = False) -> str:
    body = item["body"] if include_code else prose_body(item)
    return "\n".join(text for _, text in body)


def images(line: str) -> list[dict]:
    found = [{"alt": match.group("alt"), "url": match.group("url")} for match in IMAGE_RE.finditer(line)]
    found += [{"alt": "", "url": match.group("url")} for match in IMG_TAG_RE.finditer(line)]
    return found


def links(line: str) -> list[str]:
    return [match.group("url") for match in LINK_RE.finditer(line)]


def strip_code_and_emphasis(text: str) -> str:
    text = re.sub(r"`[^`\n]*`", "", text)
    return re.sub(r"[*_]{1,3}", "", text)


def word_count(text: str) -> int:
    return len(strip_code_and_emphasis(text).split())


def sentence_count(text: str) -> int:
    return len(re.findall(r"[.!?](?=\s|$)", strip_code_and_emphasis(text)))


def code_blocks(body: list[tuple[int, str]]) -> list[dict]:
    """Fenced blocks in a section: (info string, first content line, lines)."""
    blocks: list[dict] = []
    current: dict | None = None
    for number, line in body:
        fence = re.match(r"^\s*(?:```|~~~)\s*(?P<info>[\w+-]*)", line)
        if fence and current is None:
            current = {"info": fence.group("info"), "line": number + 1, "body": []}
            continue
        if fence and current is not None:
            blocks.append(current)
            current = None
            continue
        if current is not None:
            current["body"].append(line)
    return blocks


# --------------------------------------------------------------------------- cargo


class Cargo:
    """`cargo search` and `cargo metadata`, each run once per repository."""

    def __init__(self, directory: Path, repo: str, readme: str):
        self.directory = directory
        self.repo = repo
        self.readme_name = readme
        self._published: dict[str, str | None] = {}
        self._metadata: dict | None = None

    def published(self, name: str) -> str | None:
        if name in self._published:
            return self._published[name]
        try:
            result = subprocess.run(
                ["cargo", "search", "--limit", "1", name],
                cwd=str(self.directory), capture_output=True, text=True, timeout=180,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ToolError(f"cargo search {name} failed: {error}") from error
        if result.returncode != 0:
            raise ToolError(f"cargo search {name} failed: {result.stderr.strip()[:200]}")
        version = None
        for line in result.stdout.splitlines():
            match = re.match(rf"^{re.escape(name)} = \"(?P<version>[^\"]+)\"", line)
            if match:
                version = match.group("version")
            break
        self._published[name] = version
        return version

    def package(self) -> str:
        """The package name that stands for the repository, from cargo metadata."""
        found = package_version(self.metadata(), self.repo, self.readme_name)
        if found is None:
            raise ToolError(
                f"cannot tell the root package: the workspace has no package named {self.repo} "
                "and no `cargo add` names one")
        return found[0]

    def metadata(self) -> dict:
        if self._metadata is not None:
            return self._metadata
        try:
            result = subprocess.run(
                ["cargo", "metadata", "--no-deps", "--format-version", "1"],
                cwd=str(self.directory), capture_output=True, text=True, timeout=300,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ToolError(f"cargo metadata failed: {error}") from error
        if result.returncode != 0:
            raise ToolError(f"cargo metadata failed: {result.stderr.strip()[-300:]}")
        try:
            self._metadata = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise ToolError(f"cargo metadata printed no JSON: {error}") from error
        return self._metadata


def package_version(metadata: dict, repo: str, readme: str) -> tuple[str, str] | None:
    """(name, version) of the package that stands for this repository."""
    packages = {package["name"]: package for package in metadata.get("packages", [])}
    root = (metadata.get("resolve") or {}).get("root")
    if root:
        for package in packages.values():
            if package["id"] == root:
                return package["name"], package["version"]
    if repo in packages:
        return repo, packages[repo]["version"]
    added = re.search(r"cargo add\s+(?P<name>[A-Za-z0-9_-]+)", readme)
    if added and added.group("name") in packages:
        name = added.group("name")
        return name, packages[name]["version"]
    return None


def version_tuple(version: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", version)[:3]
    return tuple(int(part) for part in parts) + (0,) * (3 - len(parts))


# --------------------------------------------------------------------------- context


class Context:
    def __init__(self, directory: Path, entry: dict):
        self.dir = directory
        self.entry = entry
        self.repo = entry["repo"]
        readme = directory / "README.md"
        self.readme_exists = readme.is_file()
        self.readme = readme.read_text(encoding="utf-8", errors="replace") if self.readme_exists else ""
        self.cargo = Cargo(directory, self.repo, self.readme)
        self.lines = self.readme.splitlines()
        self.sections = h2_sections(self.lines) if self.readme_exists else []
        self.badge_line = find_badge_line(self.lines)
        self._rename = None

    def rename(self):
        """rename.py's forbidden-name reader, imported from beside this file."""
        if self._rename is None:
            if not RENAME.is_file():
                raise ToolError(f"no rename.py beside readme_check.py at {RENAME}")
            spec = importlib.util.spec_from_file_location("dark_inc_rename", RENAME)
            if spec is None or spec.loader is None:
                raise ToolError(f"cannot load {RENAME}")
            module = importlib.util.module_from_spec(spec)
            sys.modules["dark_inc_rename"] = module
            spec.loader.exec_module(module)
            if not hasattr(module, "forbidden_hits"):
                raise ToolError(f"{RENAME} has no forbidden_hits()")
            self._rename = module
        return self._rename


def find_badge_line(lines: list[str]) -> int | None:
    """The first line carrying two badges (`[![alt](img)](link)`)."""
    for number, line in enumerate(lines, 1):
        if line.count("[![") >= 2:
            return number
    return None


# --------------------------------------------------------------------------- README checks


def rc01(ctx: Context) -> list[tuple]:
    h1 = [(number, line) for number, line in prose_lines(ctx.lines) if re.match(r"^#\s", line)]
    if not h1:
        return [("README.md", 1, "no H1")]
    number, line = h1[0]
    if ctx.repo not in line and ctx.repo.replace("_", " ").title() not in line:
        return [("README.md", number, f"the H1 does not name {ctx.repo}")]
    return []


def rc02(ctx: Context) -> list[tuple]:
    h1 = next((number for number, line in prose_lines(ctx.lines) if re.match(r"^#\s", line)), None)
    if h1 is None:
        return [("README.md", 1, "no H1 to put the banner under")]
    for number, line in enumerate(ctx.lines[h1:h1 + BANNER_WINDOW_LINES], h1 + 1):
        if _plain(line.strip()) == _plain(BANNER):
            return []
    return [("README.md", h1, f"the Vibe Coded banner is not within {BANNER_WINDOW_LINES} lines of the H1")]


def _plain(text: str) -> str:
    return unicodedata.normalize("NFC", re.sub(r"\s+", " ", text))


def rc03(ctx: Context) -> list[tuple]:
    pitch = pitch_paragraph(ctx)
    if pitch is None:
        return [("README.md", 1, "no pitch paragraph under the banner")]
    number, text = pitch
    sentences = sentence_count(text)
    if sentences != 1:
        return [("README.md", number, f"the pitch is {sentences} sentences, not one")]
    words = word_count(text)
    if words > MAX_PITCH_WORDS:
        return [("README.md", number, f"the pitch is {words} words, over {MAX_PITCH_WORDS}")]
    return []


def pitch_paragraph(ctx: Context) -> tuple[int, str] | None:
    """The first prose paragraph under the H1: no heading, quote, badge, image or table."""
    started = False
    for number, line in prose_lines(ctx.lines):
        stripped = line.strip()
        if not started:
            if re.match(r"^#\s", line):
                started = True
            continue
        if not stripped:
            continue
        if stripped.startswith(("#", ">", "|", "<!--")) or stripped.startswith("!["):
            continue
        if "[![" in stripped:
            continue
        return number, stripped
    return None


BADGE_RE = re.compile(r"\[!\[(?P<alt>[^\]]*)\]\((?P<img>[^)\s]+)\)\]\((?P<link>[^)\s]+)\)")


def badges(line: str) -> list[dict]:
    return [match.groupdict() for match in BADGE_RE.finditer(line)]


def has_badge(found: list[dict], alt: re.Pattern, links: tuple[str, ...]) -> bool:
    return any(alt.search(badge["alt"]) or any(piece in badge["link"] + badge["img"] for piece in links)
               for badge in found)


def rc04(ctx: Context) -> list[tuple]:
    if ctx.badge_line is None:
        return [("README.md", 1, "no badge line (two or more `[![` badges on one line)")]
    line = ctx.lines[ctx.badge_line - 1]
    found = badges(line)
    number = ctx.badge_line
    findings = []
    for name, alt, links in (
        ("CI", re.compile(r"^CI$", re.IGNORECASE), ("/actions/workflows/",)),
        ("Bevy", re.compile(r"bevy \d+\.\d+", re.IGNORECASE), ("badge/bevy-",)),
        ("licence", re.compile(r"licen[cs]e", re.IGNORECASE), ("badge/licence", "badge/license")),
    ):
        if not has_badge(found, alt, links):
            findings.append(("README.md", number, f"the badge line has no {name} badge"))
    try:
        package = ctx.cargo.package()
        published = ctx.cargo.published(package)
    except ToolError as error:
        return findings + [("README.md", number, str(error))]
    crates_badge = has_badge(found, re.compile(r"crates\.io", re.IGNORECASE), ("crates.io/crates/",))
    docs_badge = has_badge(found, re.compile(r"docs\.rs", re.IGNORECASE), ("docs.rs/",))
    if published:
        if not crates_badge:
            findings.append(("README.md", number,
                             f"{package} is published but the badges carry no crates.io badge"))
        if not docs_badge:
            findings.append(("README.md", number,
                             f"{package} is published but the badges carry no docs.rs badge"))
    else:
        if docs_badge:
            findings.append(("README.md", number,
                             f"{package} is not published but the badges carry a docs.rs badge"))
        if "git only" not in line:
            findings.append(("README.md", number,
                             f"{package} is not published, so the badges must say `git only`"))
    return findings


def rc05(ctx: Context) -> list[tuple]:
    start = (ctx.badge_line or 0)
    for number, line in enumerate(ctx.lines[start:], start + 1):
        for image in images(line):
            alt_words = len(image["alt"].split())
            findings = []
            if not re.match(r"^[a-zA-Z][\w+.-]*://", image["url"]):
                findings.append(("README.md", number, f"the hero image URL is relative: {image['url']}"))
            if alt_words < MIN_CAPTION_ALT_WORDS:
                findings.append(("README.md", number, f"the hero alt text is {alt_words} words, under {MIN_CAPTION_ALT_WORDS}"))
            caption = _next_prose(ctx.lines, number)
            if caption is None or not re.match(r"^\*[^*].*\*$|^_[^_].*_$", caption[1].strip()):
                findings.append(("README.md", caption[0] if caption else number,
                                 "the hero image has no italic caption line under it"))
            return findings
    return [("README.md", 1, "no hero image after the badges")]


def _next_prose(lines: list[str], after: int) -> tuple[int, str] | None:
    for number in range(after + 1, len(lines) + 1):
        if lines[number - 1].strip():
            return number, lines[number - 1]
    return None


def rc06(ctx: Context) -> list[tuple]:
    status = [(number, line) for number, line in prose_lines(ctx.lines) if line.startswith("**Status:**")]
    if not status:
        return [("README.md", 1, "no `**Status:**` line")]
    number, line = status[0]
    match = STATUS_RE.match(line.strip())
    if match is None:
        return [("README.md", number,
                 "the status line is not `**Status:** <experimental|usable> · Bevy <x.y>[ · MSRV <x.y.z>]`")]
    try:
        metadata = ctx.cargo.metadata()
        name = ctx.cargo.package()
        published = ctx.cargo.published(name)
    except ToolError as error:
        return [("README.md", number, str(error))]
    version = next(package["version"] for package in metadata["packages"] if package["name"] == name)
    expected = "usable" if published and version_tuple(version) >= (0, 1, 0) else "experimental"
    if match.group(1) != expected:
        reason = f"{name} {version} is " + (f"published" if published else "unpublished")
        return [("README.md", number, f"the level is `{match.group(1)}` but {reason}, so it is `{expected}`")]
    return []


def rc07(ctx: Context) -> list[tuple]:
    for number, line in prose_lines(ctx.lines):
        if line.startswith("**Why:** "):
            return []
    return [("README.md", 1, "no `**Why:** ` line")]


def rc08(ctx: Context) -> list[tuple]:
    found = [(item["title"], item["line"]) for item in ctx.sections]
    findings = []
    positions: dict[str, int] = {}
    for index, (title, number) in enumerate(found):
        if title in README_H2 and title in positions:
            findings.append(("README.md", number, f"`## {title}` appears twice"))
        if title in README_H2 and title not in positions:
            positions[title] = index
    missing = [title for title in README_H2 if title not in positions]
    for title in missing:
        findings.append(("README.md", 1, f"no `## {title}` section"))
    ordered = [title for title in README_H2 if title in positions]
    for earlier, later in zip(ordered, ordered[1:]):
        if positions[earlier] > positions[later]:
            findings.append(("README.md", found[positions[later]][1],
                             f"`## {later}` comes before `## {earlier}`"))
    extras = [(index, title, number) for index, (title, number) in enumerate(found)
              if title not in README_H2]
    if len(extras) > MAX_EXTRA_H2:
        findings.append(("README.md", extras[MAX_EXTRA_H2][2],
                         f"{len(extras)} extra H2 sections, over {MAX_EXTRA_H2}"))
    if "What you can do" in positions and "Part of Dark Inc." in positions:
        low, high = positions["What you can do"], positions["Part of Dark Inc."]
        for index, title, number in extras:
            if not low < index < high:
                findings.append(("README.md", number,
                                 f"`## {title}` is an extra section outside What you can do and Part of Dark Inc."))
    return findings


def rc09(ctx: Context) -> list[tuple]:
    quick = section(ctx.sections, "Quick start")
    if quick is None:
        return []
    text = section_text(quick, include_code=True)
    findings = []
    has_install = re.search(r"cargo add\s", text) or re.search(r"git\s*=", text)
    if not has_install:
        findings.append(("README.md", quick["line"], "Quick start has no `cargo add` or git-dependency line"))
    for block in code_blocks(quick["body"]):
        if block["info"] in ("rust", "rs", ""):
            if len(block["body"]) > MAX_QUICKSTART_RUST_LINES:
                findings.append(("README.md", block["line"],
                                 f"the Quick start Rust block is {len(block['body'])} lines, over {MAX_QUICKSTART_RUST_LINES}"))
    return findings


def rc10(ctx: Context) -> list[tuple]:
    try_it = section(ctx.sections, "Try it")
    if try_it is None:
        return []
    if "cargo run" in section_text(try_it, include_code=True):
        return []
    return [("README.md", try_it["line"], "Try it has no `cargo run` line")]


def rc11(ctx: Context) -> list[tuple]:
    what = section(ctx.sections, "What you can do")
    if what is None:
        return []
    body = prose_body(what)
    bullets = [(number, text) for number, text in body if re.match(r"^- ", text)]
    findings = []
    if not MIN_BULLETS <= len(bullets) <= MAX_BULLETS:
        findings.append(("README.md", what["line"],
                         f"What you can do has {len(bullets)} bullets, not {MIN_BULLETS}-{MAX_BULLETS}"))
    for number, text in bullets:
        if not links(text):
            findings.append(("README.md", number, "the bullet links nothing"))
    pictures = sum(len(images(text)) for _, text in body)
    if pictures > MAX_SECTION_IMAGES:
        findings.append(("README.md", what["line"],
                         f"What you can do has {pictures} images, over {MAX_SECTION_IMAGES}"))
    return findings


def rc12(ctx: Context) -> list[tuple]:
    family = section(ctx.sections, "Part of Dark Inc.")
    if family is None:
        return []
    text = section_text(family)
    findings = []
    if ORG_URL not in text:
        findings.append(("README.md", family["line"], f"Part of Dark Inc. does not link {ORG_URL}"))
    chapter = f"{BOOK_CRATE_URL}/{ctx.repo}/"
    if chapter not in text:
        findings.append(("README.md", family["line"], f"Part of Dark Inc. does not link {chapter}"))
    return findings


def rc13(ctx: Context) -> list[tuple]:
    compatibility = section(ctx.sections, "Bevy compatibility")
    if compatibility is None:
        return []
    body = prose_body(compatibility)
    for index, (_, text) in enumerate(body):
        if text.strip().startswith("|") and index + 1 < len(body):
            if re.match(r"^\|[\s:|-]+\|$", body[index + 1][1].strip()):
                return []
    return [("README.md", compatibility["line"], "Bevy compatibility has no table")]


def rc14(ctx: Context) -> list[tuple]:
    learn = section(ctx.sections, "Learn more")
    if learn is None:
        return []
    number = learn["line"]
    text = section_text(learn)
    urls = [url for _, line in prose_body(learn) for url in links(line)]
    findings = []
    if "docs.rs/" not in text and "unpublished" not in text:
        findings.append(("README.md", number, "Learn more links neither docs.rs nor says `unpublished`"))
    chapter = f"{BOOK_CRATE_URL}/{ctx.repo}/"
    if not any(chapter in url or url.rstrip("/") == chapter.rstrip("/") for url in urls):
        findings.append(("README.md", number, f"Learn more does not link the book chapter {chapter}"))
    if not any("docs/guide/" in url for url in urls):
        findings.append(("README.md", number, "Learn more does not link `docs/guide/`"))
    if not any("CHANGELOG.md" in url for url in urls):
        findings.append(("README.md", number, "Learn more does not link `CHANGELOG.md`"))
    return findings


def rc15(ctx: Context) -> list[tuple]:
    who = section(ctx.sections, "Who and licence")
    if who is None:
        return []
    text = section_text(who)
    findings = []
    for piece in ("@Ladvien", "MIT OR Apache-2.0"):
        if piece not in text:
            findings.append(("README.md", who["line"], f"Who and licence does not name `{piece}`"))
    if not any("CONTRIBUTING.md" in url for _, line in prose_body(who) for url in links(line)):
        findings.append(("README.md", who["line"], "Who and licence does not link the org's CONTRIBUTING.md"))
    return findings


def rc16(ctx: Context) -> list[tuple]:
    count = len(ctx.lines)
    if count > MAX_README_LINES:
        return [("README.md", count, f"{count} lines > {MAX_README_LINES}")]
    return []


def rc17(ctx: Context) -> list[tuple]:
    """Every image and repository link is absolute and points at dark-incorporated.

    The badge line is exempt: its images are shields.io badges, measured by RC04.
    """
    findings = []
    for number, line in prose_lines(ctx.lines):
        if number == ctx.badge_line:
            continue
        for image in images(line):
            url = image["url"]
            if url.startswith("https://img.shields.io/"):
                continue
            match = REPO_PATH_URL_RE.match(url)
            if match is None:
                findings.append(("README.md", number,
                                 f"the image {url} is not https://raw.githubusercontent.com/{ORG}/{ctx.repo}/main/..."))
            elif match.group("repo") != ctx.repo:
                findings.append(("README.md", number,
                                 f"the image {url} belongs to {match.group('repo')}, not {ctx.repo}"))
        for url in links(line):
            if url.startswith("#") or re.match(r"^[a-zA-Z][\w+.-]*:", url):
                match = REPO_BLOB_URL_RE.match(url)
                if match and match.group("repo") == ctx.repo and match.group("org") != ORG:
                    findings.append(("README.md", number,
                                     f"the link {url} names {match.group('org')}, not {ORG}"))
                if url.startswith("https://raw.githubusercontent.com/"):
                    raw = REPO_PATH_URL_RE.match(url)
                    if raw and raw.group("repo") == ctx.repo and not url.startswith(f"{RAW_URL}/"):
                        findings.append(("README.md", number, f"the link {url} does not name {ORG}"))
                continue
            findings.append(("README.md", number, f"the link {url} is relative; a README link is absolute"))
    return findings


def rc18(ctx: Context) -> list[tuple]:
    for _, line in prose_lines(ctx.lines):
        for image in images(line):
            path = image["url"].split("#")[0].split("?")[0].lower()
            if path.endswith(STILL_SUFFIXES):
                return []
    return [("README.md", 1, "no still image (.png, .jpg or .svg)")]


def rc19(ctx: Context) -> list[tuple]:
    try:
        metadata = ctx.cargo.metadata()
    except ToolError as error:
        return [("README.md", 1, str(error))]
    hook = 'include_str!("../README.md")'
    checked = 0
    for package in metadata.get("packages", []):
        directory = Path(package["manifest_path"]).parent
        candidates = [directory / "src" / "lib.rs"] + sorted((directory / "tests").glob("*.rs"))
        for candidate in candidates:
            if not candidate.is_file():
                continue
            checked += 1
            text = candidate.read_text(encoding="utf-8", errors="replace")
            if hook in text and "#[cfg(doctest)]" in text:
                return []
    if checked == 0:
        return [("README.md", 1, "no workspace member has src/lib.rs or tests/*.rs")]
    return [("README.md", 1, f'no `#[cfg(doctest)]` hook with {hook} in a src/lib.rs or tests/*.rs')]


def rc20(ctx: Context) -> list[tuple]:
    try:
        rename = ctx.rename()
    except ToolError as error:
        return [("README.md", 1, str(error))]
    seen: set[tuple[int, str]] = set()
    findings = []
    for number, text in rename.forbidden_hits(ctx.readme):
        if (number, text) in seen:
            continue
        seen.add((number, text))
        findings.append(("README.md", number, f"forbidden name `{text}`"))
    return findings


# --------------------------------------------------------------------------- guidance checks


def documentation(ctx: Context) -> tuple[Path, list[str]] | None:
    target = ctx.dir / "DOCUMENTATION.md"
    if not target.is_file():
        return None
    return target, target.read_text(encoding="utf-8", errors="replace").splitlines()


def dc01(ctx: Context) -> list[tuple]:
    document = documentation(ctx)
    if document is None:
        return [("DOCUMENTATION.md", 0, "DOCUMENTATION.md is missing")]
    lines = document[1]
    if len(lines) > MAX_DOC_LINES:
        return [("DOCUMENTATION.md", len(lines), f"{len(lines)} lines > {MAX_DOC_LINES}")]
    return []


def dc02(ctx: Context) -> list[tuple]:
    document = documentation(ctx)
    if document is None:
        return []
    lines = document[1]
    start = next((index for index, line in enumerate(lines) if re.match(r"^#\s", line)), -1)
    paragraph = []
    for line in lines[start + 1:]:
        if not line.strip():
            if paragraph:
                break
            continue
        paragraph.append(line)
    text = "\n".join(paragraph)
    if DOC_GUIDE_URL in text and STYLE_GUIDE_URL in text:
        return []
    return [("DOCUMENTATION.md", start + 2, "the first paragraph does not link both org guides")]


def dc03(ctx: Context) -> list[tuple]:
    document = documentation(ctx)
    if document is None:
        return []
    target, lines = document
    text = "\n".join(lines)
    if BEGIN_MARKER not in text or END_MARKER not in text:
        return [("DOCUMENTATION.md", 1, "no dark-inc:generated markers")]
    if not REPO_DOC.is_file():
        return [("DOCUMENTATION.md", 1, f"no repo_doc.py beside readme_check.py at {REPO_DOC}")]
    between = text.split(BEGIN_MARKER, 1)[1].split(END_MARKER, 1)[0].strip("\n")
    command = [sys.executable, str(REPO_DOC), "--repo", str(ctx.dir), "--print"]
    if ctx.entry_path is not None:
        command += ["--entry-json", str(ctx.entry_path)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        return [("DOCUMENTATION.md", 1, f"repo_doc.py --print failed: {result.stderr.strip()}")]
    rendered = result.stdout.strip("\n")
    if rendered != between:
        offset = _first_difference(between.splitlines(), rendered.splitlines())
        line = _line_of(lines, BEGIN_MARKER) + 1 + offset
        return [("DOCUMENTATION.md", line,
                 "the generated block differs from `repo_doc.py --repo . --print`; run it to refresh")]
    return []


def _line_of(lines: list[str], needle: str) -> int:
    return next(index for index, line in enumerate(lines, 1) if needle in line)


def _first_difference(actual: list[str], expected: list[str]) -> int:
    for index, (left, right) in enumerate(zip(actual, expected)):
        if left != right:
            return index
    return min(len(actual), len(expected))


def dc04(ctx: Context) -> list[tuple]:
    document = documentation(ctx)
    if document is None:
        return []
    _, lines = document
    titles = [item["title"] for item in h2_sections(lines)]
    if titles == DOC_H2:
        return []
    findings = []
    for title in titles:
        if title not in DOC_H2:
            findings.append(("DOCUMENTATION.md", 1, f"`## {title}` is not one of {', '.join(DOC_H2)}"))
    for title in DOC_H2:
        if title not in titles:
            findings.append(("DOCUMENTATION.md", 1, f"no `## {title}` section"))
    if not findings and titles != DOC_H2:
        findings.append(("DOCUMENTATION.md", 1, f"the H2s are out of order: {', '.join(titles)}"))
    return findings


def dc05(ctx: Context) -> list[tuple]:
    findings = []
    present = 0
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = ctx.dir / name
        if not path.is_file():
            continue
        present += 1
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if DC05_LINE not in [line.strip() for line in lines]:
            findings.append((name, 1, "no DC05 pointer line to ./DOCUMENTATION.md"))
        for number, line in enumerate(lines, 1):
            if OLD_GUIDE_LINK.search(line):
                findings.append((name, number, "links an older docs guide instead of ./DOCUMENTATION.md"))
    if present == 0:
        findings.append(("AGENTS.md", 0, "neither AGENTS.md nor CLAUDE.md exists"))
    return findings


# --------------------------------------------------------------------------- driver



def rc21(ctx: Context) -> list[tuple]:
    findings = []
    for number, line in prose_lines(ctx.lines):
        if number == ctx.badge_line:
            continue
        for image in images(line):
            path = repo_path(ctx, image["url"])
            if path is None:
                continue
            target = ctx.dir / path
            if not target.is_file():
                findings.append(("README.md", number, f"{path} does not exist in the repository"))
                continue
            size = target.stat().st_size
            if size > MAX_MEDIA_BYTES:
                findings.append(("README.md", number, f"{path} is {size / 1e6:.1f} MB, over 4 MB"))
            if path.lower().endswith(".gif"):
                width = gif_width(target)
                if width is not None and width > MAX_GIF_WIDTH_PX:
                    findings.append(("README.md", number, f"{path} is {width} px wide, over {MAX_GIF_WIDTH_PX}"))
    return findings


README_CHECKS = [
    ("RC01", rc01), ("RC02", rc02), ("RC03", rc03), ("RC04", rc04), ("RC05", rc05),
    ("RC06", rc06), ("RC07", rc07), ("RC08", rc08), ("RC09", rc09), ("RC10", rc10),
    ("RC11", rc11), ("RC12", rc12), ("RC13", rc13), ("RC14", rc14), ("RC15", rc15),
    ("RC16", rc16), ("RC17", rc17), ("RC18", rc18), ("RC19", rc19), ("RC20", rc20),
    ("RC21", rc21),
]
DOC_CHECKS = [
    ("DC01", dc01), ("DC02", dc02), ("DC03", dc03), ("DC04", dc04), ("DC05", dc05),
]

ANY_ORG_RAW_URL_RE = re.compile(
    r"^https://raw\.githubusercontent\.com/(?P<org>[^/]+)/(?P<repo>[^/]+)/(?:main|[0-9a-f]{7,40})/(?P<path>.+)$"
)


def repo_path(ctx: Context, url: str) -> str | None:
    """The repository-relative path an image names, whichever org the URL spells."""
    match = ANY_ORG_RAW_URL_RE.match(url)
    if match:
        return match.group("path") if match.group("repo") == ctx.repo else None
    if re.match(r"^[a-zA-Z][\w+.-]*:", url):
        return None
    return url.split("#")[0].split("?")[0]


def gif_width(path: Path) -> int | None:
    try:
        from PIL import Image
    except ImportError as error:
        raise ToolError(f"Pillow is not installed: {error}") from error
    try:
        with Image.open(path) as image:
            return image.size[0]
    except OSError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True, metavar="DIR", help="the crate repository")
    parser.add_argument("--json", metavar="OUT", help="write the checks as JSON here")
    parser.add_argument("--entry-json", metavar="FILE",
                        help="one crates.json-shaped entry instead of the origin lookup")
    args = parser.parse_args()

    directory = Path(args.repo).resolve()
    if not directory.is_dir():
        die(f"{directory} is not a directory")

    entry = find_entry(directory, args.entry_json)
    ctx = Context(directory, entry)
    ctx.entry_path = Path(args.entry_json).resolve() if args.entry_json else None

    checks: list[dict] = []
    failures = 0
    for check_id, check in README_CHECKS + DOC_CHECKS:
        if not ctx.readme_exists and check_id.startswith("RC"):
            found = [("README.md", 0, "README.md is missing")]
        else:
            try:
                found = check(ctx)
            except ToolError as error:
                found = [("README.md", 0, str(error))]
        for file, line, message in found:
            failures += 1
            print(f"{check_id} FAIL {file}:{line} {message}")
        checks.append({
            "id": check_id,
            "ok": not found,
            "file": found[0][0] if found else None,
            "line": found[0][1] if found else None,
            "message": "\n".join(message for _, _, message in found),
        })

    if args.json:
        Path(args.json).write_text(json.dumps({"repo": ctx.repo, "checks": checks}, indent=2) + "\n")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
