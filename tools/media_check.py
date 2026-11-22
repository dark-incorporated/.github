#!/usr/bin/env python3
"""Check a crate repository's media manifest, budgets and staleness.

    media_check.py --repo DIR [--json OUT] [--stale] [--stale-json OUT]

The manifest is `docs/media/README.md`, whose canonical table is

    | File | Command | Captured | Watches | Shows |

MC01 measures the rows, MC02 that each file exists, MC03 the GIF budget (a GIF is
3-8 s, at most 960 px wide, at most 15 fps and at most 4 MB; an MP4 is refused
because video lives only in the book), MC04 that every image the README and the
guide show has a row, and MC05 -- only with `--stale` -- that the row's capture
still matches the code.

A GIF's frame rate is measured as 1000 x frames / total duration, because a 15 fps
frame is 66.67 ms and an encoder rounds that to 60 or 70 ms per frame: reading each
frame's own delay would fail a genuine 15 fps GIF, and the mean with a small
tolerance for that rounding is what tells a 15 fps GIF from a 20 fps one.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

MANIFEST = Path("docs") / "media" / "README.md"
CANONICAL_HEADER = ["File", "Command", "Captured", "Watches", "Shows"]
CAPTURE_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2}) (?P<sha>[0-9a-f]{7,40})$")
BACKTICKED_PATH_RE = re.compile(r"`(?P<path>[^`]+)`")
SEPARATOR_RE = re.compile(r"^\|[\s:|-]+\|$")
IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\(\s*(?P<url>[^)\s]+)")
IMG_TAG_RE = re.compile(r"<img\s[^>]*?src=\"(?P<url>[^\"]+)\"", re.IGNORECASE)
RAW_URL_RE = re.compile(
    r"^https://raw\.githubusercontent\.com/[^/]+/(?P<repo>[^/]+)/(?P<ref>[^/]+)/(?P<path>.+)$"
)
GUIDE_GLOBS = ("docs/guide/*.md", "docs/guide/**/*.md")

MIN_GIF_SECONDS = 3.0
MAX_GIF_SECONDS = 8.0
# A 15 fps frame lasts 66.67 ms; an encoder rounds that to 60 or 70 ms, so a genuine
# 15 fps GIF's mean can read as 15.4 fps. The tolerance covers that rounding only.
MAX_GIF_FPS = 15
GIF_FPS_TOLERANCE = 0.05
MAX_GIF_WIDTH_PX = 960
MAX_MEDIA_BYTES = 4 * 1024 * 1024
GIF_SUFFIX = ".gif"
MP4_SUFFIXES = (".mp4", ".mov", ".webm")


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


def git(directory: Path, *arguments: str) -> tuple[int, str]:
    result = subprocess.run(["git", "-C", str(directory), *arguments], capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr).strip()


# --------------------------------------------------------------------------- manifest


def split_row(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [cell.strip() for cell in body.split("|")]


def read_manifest(directory: Path) -> list[tuple[int, str]] | None:
    path = directory / MANIFEST
    if not path.is_file():
        return None
    return list(enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1))


def table_rows(directory: Path) -> tuple[list[dict], set[str], list[tuple]]:
    """The manifest's rows, every backticked File it declares, and the MC01 findings.

    Columns are read by their header name, so an older four-column manifest still
    yields rows for MC02 and MC03 while MC01 reports the columns the canonical
    table wants. A row that cannot be parsed is still a declaration: MC04 asks
    whether an image has a row, MC01 asks whether that row is well formed.
    """
    manifest = read_manifest(directory)
    if manifest is None:
        return [], set(), [("docs/media/README.md", 0,
                            "documents no media: docs/media/README.md is missing")]
    findings: list[tuple] = []
    rows: list[dict] = []
    declared: set[str] = set()
    columns: dict[str, int] | None = None
    header: list[str] = []
    seen_header = False
    for number, line in manifest:
        cells = split_row(line) if line.strip().startswith("|") else None
        if cells is None:
            columns = None
            continue
        if columns is None and not seen_header:
            seen_header = True
            header = cells
            if not cells or cells[0] != CANONICAL_HEADER[0]:
                findings.append(("docs/media/README.md", number,
                                 f"no table headed | {' | '.join(CANONICAL_HEADER)} |"))
                continue
            columns = {name: index for index, name in enumerate(cells)}
            missing = [name for name in CANONICAL_HEADER if name not in columns]
            if missing:
                findings.append(("docs/media/README.md", number,
                                 f"the manifest table is missing the column(s) {' and '.join(missing)}; "
                                 f"the canonical table is | {' | '.join(CANONICAL_HEADER)} |"))
            continue
        if columns is None or SEPARATOR_RE.match(line.strip()):
            continue
        if len(cells) != len(header):
            findings.append(("docs/media/README.md", number,
                             f"{len(cells)} cells, not {len(header)}: one per column of the header"))
            continue

        def cell(name: str) -> str | None:
            index = columns.get(name)
            return cells[index].strip() if index is not None else None

        file_cell = cell("File") or ""
        # A row declares its file even when the cell is malformed: MC01 says the cell
        # is wrong, MC04 only asks whether the file has a row at all.
        anywhere = BACKTICKED_PATH_RE.search(file_cell)
        if anywhere is not None:
            declared.add(media_path(anywhere.group("path")).as_posix())
        name_match = re.fullmatch(r"`(?P<path>[^`]+)`", file_cell)
        if name_match is None:
            findings.append(("docs/media/README.md", number,
                             f"the File cell is not a bare backticked path: {file_cell}"))
            continue
        file_path = name_match.group("path")
        path = media_path(file_path)

        captured = cell("Captured")
        capture_match = CAPTURE_RE.fullmatch(captured) if captured is not None else None
        if capture_match is None:
            findings.append(("docs/media/README.md", number,
                             f"Captured is not `YYYY-MM-DD <sha7+>`: {captured or 'missing'}"))
        command = (cell("Command") or "").strip("`").strip()
        if not command:
            findings.append(("docs/media/README.md", number, "the Command cell is empty"))
        watches = cell("Watches")
        if watches is None:
            pass
        elif watches != "-" and not all(glob.strip("`").strip() for glob in watches.split(",")):
            findings.append(("docs/media/README.md", number, f"Watches is not globs or `-`: {watches}"))
        shows = cell("Shows")
        if shows is not None and not shows:
            findings.append(("docs/media/README.md", number, "the Shows cell is empty"))
        rows.append({
            "line": number,
            "file": file_path,
            "path": path,
            "command": command,
            "date": capture_match.group("date") if capture_match else None,
            "sha": capture_match.group("sha") if capture_match else None,
            "watches": [] if watches in (None, "-") else [glob.strip("`").strip() for glob in watches.split(",")],
            "watches_raw": watches,
            "watches_known": watches is not None,
            "shows": shows or "",
        })
    return rows, declared, findings


def media_path(name: str) -> Path:
    """A row's File cell as a repository-relative path."""
    if name.startswith("docs/"):
        return Path(name)
    return MANIFEST.parent / name


def manifest_md(directory: Path) -> Path:
    return directory / MANIFEST


# --------------------------------------------------------------------------- checks


def mc01(rows: list[dict], findings: list[tuple]) -> list[tuple]:
    return findings


def mc02(directory: Path, rows: list[dict]) -> list[tuple]:
    return [(f"docs/media/README.md", row["line"], f"{row['path']} does not exist")
            for row in rows if not (directory / row["path"]).is_file()]


def mc03(directory: Path, rows: list[dict]) -> list[tuple]:
    findings = []
    for row in rows:
        path = directory / row["path"]
        suffix = path.suffix.lower()
        if suffix in MP4_SUFFIXES:
            findings.append(("docs/media/README.md", row["line"],
                             f"{row['path']} is {suffix}: video lives only in the book"))
            continue
        if not path.is_file():
            continue
        size = path.stat().st_size
        if size > MAX_MEDIA_BYTES:
            findings.append(("docs/media/README.md", row["line"],
                             f"{row['path']} is {size / 1e6:.2f} MB, over 4 MB"))
        if suffix != GIF_SUFFIX:
            continue
        try:
            width, seconds, fps = gif_budget(path)
        except ToolError as error:
            findings.append(("docs/media/README.md", row["line"], str(error)))
            continue
        if width > MAX_GIF_WIDTH_PX:
            findings.append(("docs/media/README.md", row["line"],
                             f"{row['path']} is {width} px wide, over {MAX_GIF_WIDTH_PX}"))
        if not MIN_GIF_SECONDS <= seconds <= MAX_GIF_SECONDS:
            findings.append(("docs/media/README.md", row["line"],
                             f"{row['path']} runs {seconds:.1f} s, not {MIN_GIF_SECONDS:.0f}-{MAX_GIF_SECONDS:.0f} s"))
        if fps > MAX_GIF_FPS * (1 + GIF_FPS_TOLERANCE):
            findings.append(("docs/media/README.md", row["line"],
                             f"{row['path']} runs {fps:.1f} fps, over {MAX_GIF_FPS}"))
    return findings


def gif_budget(path: Path) -> tuple[int, float, float]:
    try:
        from PIL import Image, ImageSequence
    except ImportError as error:
        raise ToolError(f"Pillow is not installed: {error}") from error
    try:
        with Image.open(path) as image:
            if image.format != "GIF":
                raise ToolError(f"{path} is not a GIF")
            durations = [frame.info.get("duration", 0) for frame in ImageSequence.Iterator(image)]
            width = image.size[0]
    except OSError as error:
        raise ToolError(f"{path} cannot be read: {error}") from error
    if not durations:
        raise ToolError(f"{path} has no frames")
    total_ms = sum(durations)
    if total_ms == 0:
        raise ToolError(f"{path} carries no frame durations")
    return width, total_ms / 1000.0, len(durations) * 1000.0 / total_ms


def referenced_media(directory: Path, repo: str) -> list[tuple[str, int, Path]]:
    """(document, line, repository-relative path) for every image resolving into this repo."""
    documents: list[Path] = []
    for pattern in ("README.md", *GUIDE_GLOBS):
        for document in sorted(directory.glob(pattern)):
            if document.is_file() and document not in documents:
                documents.append(document)
    found: list[tuple[str, int, Path]] = []
    for document in documents:
        for number, line in enumerate(document.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for match in list(IMAGE_RE.finditer(line)) + list(IMG_TAG_RE.finditer(line)):
                path = repository_path(match.group("url"), repo, document.parent, directory)
                if path is not None:
                    found.append((str(document.relative_to(directory)), number,
                                  path.resolve().relative_to(directory)))
    return found


def repository_path(url: str, repo: str, document: Path, root: Path) -> Path | None:
    """A URL's repository-relative path when it points into this repository.

    An absolute raw URL carries the path from the repository root; a relative one
    is resolved against the document that shows it, as GitHub resolves it.
    """
    raw = RAW_URL_RE.match(url)
    if raw:
        if raw.group("repo") != repo:
            return None
        return (root / raw.group("path")).resolve()
    if re.match(r"^[a-zA-Z][\w+.-]*:", url):
        return None
    return (document / url.split("#")[0].split("?")[0]).resolve()


def mc04(directory: Path, declared: set[str], repo: str) -> list[tuple]:
    if not (directory / MANIFEST).is_file():
        return []
    findings = []
    for document, number, path in referenced_media(directory, repo):
        if path.as_posix() in declared:
            continue
        findings.append((document, number, f"{path.as_posix()} has no row in docs/media/README.md"))
    return findings


def mc05(directory: Path, rows: list[dict]) -> list[dict]:
    """Rows whose capture no longer matches HEAD, with the reason."""
    stale = []
    head, _ = git(directory, "rev-parse", "--verify", "HEAD")
    if head != 0:
        raise ToolError(f"{directory} has no HEAD commit to compare against")
    for row in rows:
        if row["sha"] is None:
            continue
        code, _ = git(directory, "cat-file", "-e", f"{row['sha']}^{{commit}}")
        if code != 0:
            stale.append({**row, "reason": f"capture sha {row['sha']} is not a commit"})
            continue
        code, _ = git(directory, "merge-base", "--is-ancestor", row["sha"], "HEAD")
        if code != 0:
            stale.append({**row, "reason": f"capture sha {row['sha']} is not an ancestor of HEAD"})
            continue
        if not row["watches_known"]:
            stale.append({**row, "reason": "no Watches column, so staleness cannot be measured"})
            continue
        if not row["watches"]:
            continue
        code, output = git(directory, "log", "--oneline", f"{row['sha']}..HEAD", "--", *row["watches"])
        if code != 0:
            raise ToolError(f"git log failed while measuring {row['path']}: {output[:200]}")
        if output:
            stale.append({**row, "reason": f"watched files changed since {row['sha']}"})
    return stale


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True, metavar="DIR", help="the crate repository")
    parser.add_argument("--json", metavar="OUT", help="write the checks as JSON here")
    parser.add_argument("--stale", action="store_true", help="also measure staleness (MC05)")
    parser.add_argument("--stale-json", metavar="OUT", help="write the stale rows as JSON here")
    parser.add_argument("--repo-name", metavar="NAME",
                        help="the repository name, for a directory with no origin remote")
    args = parser.parse_args()

    directory = Path(args.repo).resolve()
    if not directory.is_dir():
        die(f"{directory} is not a directory")

    repo = origin_repo(directory, args.repo_name)
    rows, declared, parse_findings = table_rows(directory)

    checks: list[dict] = []
    stale: list[dict] = []
    failures = 0

    def record(check_id: str, found: list[tuple]) -> None:
        nonlocal failures
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

    for check_id, thunk in (
        ("MC01", lambda: mc01(rows, parse_findings)),
        ("MC02", lambda: mc02(directory, rows)),
        ("MC03", lambda: mc03(directory, rows)),
        ("MC04", lambda: mc04(directory, declared, repo)),
    ):
        try:
            found = thunk()
        except ToolError as error:
            found = [("docs/media/README.md", 0, str(error))]
        record(check_id, found)

    if args.stale:
        try:
            stale = mc05(directory, rows)
            found = [("docs/media/README.md", row["line"], f"{row['path']} is stale: {row['reason']}")
                     for row in stale]
        except ToolError as error:
            found = [("docs/media/README.md", 0, str(error))]
        record("MC05", found)

    if args.stale_json:
        Path(args.stale_json).write_text(json.dumps(
            [{"file": row["path"].as_posix(), "command": row["command"], "watches": row["watches"]}
             for row in stale], indent=2) + "\n")

    if args.json:
        Path(args.json).write_text(json.dumps({"repo": repo, "checks": checks}, indent=2) + "\n")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
