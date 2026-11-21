#!/usr/bin/env python3
"""Create a new Dark Inc. crate from `dark-incorporated/bevy_crate_template`.

    new_crate.py <crate> --title T --pitch P --why W --part PART --subset SUBSET \
        --chapter-subject S --quality-bar Q [--dry-run DIR [--header PNG]]

A real run creates the GitHub repository, generates its chapter art through Retro Diffusion, runs the
local gate, pushes `main`, sets the repository up, registers its CI runner and opens two pull
requests: one on `dark-incorporated/.github` (registry, art, profile table) and one on the book
(synced guide pages and the chapter). It does not start the crate's build loop.

`--dry-run DIR` copies the local template (`$DI/bevy_crate_template`) to DIR, fills the placeholders,
uses a header image you name with `--header` (default: the generated chapter art of bevy_orca),
renders DOCUMENTATION.md from an in-memory registry entry and runs the same gate. It touches no
GitHub repository, no Retro Diffusion call, no crates.json and no repos.txt.

Every refusal exits 1 with its message on stderr. There is one path: a failing step stops the run
and nothing later is attempted.
"""

import argparse
import datetime
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GH_DIR = HERE.parent
CRATES_JSON = GH_DIR / "crates.json"
PALETTE_JSON = GH_DIR / "art" / "palette.json"

DI = Path(os.environ.get("DI", str(Path.home() / "dark-incorporated")))
ORG = "dark-incorporated"
TEMPLATE_REPO = f"{ORG}/bevy_crate_template"
TEMPLATE_DIR = DI / "bevy_crate_template"
BOOK_REPO = "dark-incorporated.github.io"
STATE_ROOT = Path.home() / ".local" / "state" / "dark-inc-docs"
RUNNERS_DIR = Path.home() / "home-cloud" / "gh-runners"
CARGO_TARGET_DIR = Path.home() / ".cargo-target-shared" / "global"
LOOP_DRIVER = DI / "bevy_dark_factory" / "tools" / "loop" / "wiggum.sh"

CRATE_NAME_RE = re.compile(r"^bevy_[a-z0-9_]+$")
PLACEHOLDER_RE = re.compile(r"(?<!\$)\{\{")  # a `${{ ... }}` is a GitHub Actions expression, not a placeholder
MANIFEST_SHA_RE = re.compile(r"(\d{4}-\d{2}-\d{2}) (<sha>|[0-9a-f]{7,40})")
SKIPPED_DIRS = frozenset({".git", "target"})

ART_BUDGET_USD = 5
RUNNER_SLOTS = 1
STAND_IN_HEADER = GH_DIR / "art" / "chapters" / "bevy_orca.png"
HEADER_PATH = "docs/media/header.png"
MANIFEST_PATH = "docs/media/README.md"
GIT_IDENTITY = ("-c", "user.name=new_crate.py", "-c", "user.email=new_crate@localhost")
REPO_TOPICS = ("bevy", "gamedev", "dark-incorporated")
LABELS = ("consumer", "consumer:bevy_dark_factory")


class Refusal(Exception):
    """A step that cannot continue. The message is the whole explanation."""


def fail(message: str) -> None:
    raise Refusal(message)


def run(cmd: list[str], cwd: Path | None = None, env: dict | None = None, capture: bool = False) -> str:
    """Run one command; a non-zero exit stops the run with the command's own output on screen."""
    result = subprocess.run(
        cmd, cwd=cwd, env=env, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )
    if result.returncode != 0:
        shown = f"\n{result.stdout}" if capture and result.stdout else ""
        fail(f"`{' '.join(cmd)}` exited {result.returncode}{shown}")
    return result.stdout if capture else ""


def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        fail(f"{path} is missing")
    except json.JSONDecodeError as error:
        fail(f"{path} is not JSON: {error}")


def pascal_case(crate: str) -> str:
    """`bevy_rust_belt` becomes `RustBelt`."""
    return "".join(word.capitalize() for word in crate.removeprefix("bevy_").split("_"))


def load_readme_check():
    """Reuse the README check's own sentence and word counting, so RC03 has one definition."""
    spec = importlib.util.spec_from_file_location("readme_check", HERE / "readme_check.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def github_has_repo(crate: str) -> bool:
    result = subprocess.run(
        ["gh", "api", f"repos/{ORG}/{crate}"], text=True, capture_output=True
    )
    if result.returncode == 0:
        return True
    if "404" in result.stderr or "Not Found" in result.stderr:
        return False
    fail(f"cannot tell whether {ORG}/{crate} exists: {result.stderr.strip()}")


def validate(args: argparse.Namespace, entries: list[dict], palette: dict) -> None:
    if not CRATE_NAME_RE.match(args.crate):
        fail("crate name must be bevy_<snake_case>")
    if any(entry["repo"] == args.crate for entry in entries):
        fail(f"{args.crate} is already in crates.json")
    if args.dry_run is None and github_has_repo(args.crate):
        fail(f"{ORG}/{args.crate} already exists")
    parts = sorted({entry["part"] for entry in entries})
    if args.part not in parts:
        fail(f"--part must be one of: {', '.join(parts)}")
    if args.subset not in palette["subsets"]:
        fail(f"--subset must be one of: {', '.join(sorted(palette['subsets']))}")
    readme_check = load_readme_check()
    words = readme_check.word_count(args.pitch)
    sentences = readme_check.sentence_count(args.pitch)
    if sentences != 1 or words > readme_check.MAX_PITCH_WORDS:
        fail(
            f"--pitch must be one sentence of at most {readme_check.MAX_PITCH_WORDS} words "
            f"(RC03): it has {sentences} sentence(s) and {words} words"
        )
    if not args.quality_bar.strip():
        fail("--quality-bar must not be empty")
    for flag in ("title", "why", "chapter_subject"):
        if not getattr(args, flag).strip():
            fail(f"--{flag.replace('_', '-')} must not be empty")


def placeholders(args: argparse.Namespace) -> dict[str, str]:
    return {
        "{{crate}}": args.crate,
        "{{Crate}}": pascal_case(args.crate),
        "{{title}}": args.title,
        "{{pitch}}": args.pitch,
        "{{why}}": args.why,
        "{{part}}": args.part,
        "{{subset}}": args.subset,
        "{{chapter_subject}}": args.chapter_subject,
        "{{quality_bar}}": args.quality_bar,
        "{{date}}": datetime.date.today().isoformat(),
    }


def tree_files(root: Path):
    for directory, names, files in os.walk(root):
        names[:] = [name for name in names if name not in SKIPPED_DIRS]
        for file in files:
            yield Path(directory) / file


def substitute(root: Path, mapping: dict[str, str]) -> None:
    for path in tree_files(root):
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        replaced = text
        for needle, value in mapping.items():
            replaced = replaced.replace(needle, value)
        if replaced != text:
            path.write_text(replaced)
    left = []
    for path in tree_files(root):
        try:
            lines = path.read_text().splitlines()
        except UnicodeDecodeError:
            continue
        left += [f"{path.relative_to(root)}:{n}: {line}" for n, line in enumerate(lines, 1)
                 if PLACEHOLDER_RE.search(line)]
    if left:
        fail("placeholders left after substitution:\n" + "\n".join(left))


def fill_manifest_sha(root: Path, sha: str) -> None:
    manifest = root / MANIFEST_PATH
    text = manifest.read_text()
    filled, count = MANIFEST_SHA_RE.subn(lambda m: f"{m.group(1)} {sha}", text)
    if count == 0:
        fail(f"{MANIFEST_PATH} has no `YYYY-MM-DD <sha>` cell to fill")
    manifest.write_text(filled)


def head_sha(root: Path) -> str:
    return run(["git", "rev-parse", "--short=7", "HEAD"], cwd=root, capture=True).strip()


def gate(root: Path, tools: Path, entry_json: Path | None, repo_name: str | None) -> None:
    """The local gate. Every command must pass; the first failure stops the run."""
    env = {**os.environ, "CARGO_TARGET_DIR": str(CARGO_TARGET_DIR)}
    CARGO_TARGET_DIR.mkdir(parents=True, exist_ok=True)
    for cmd in (
        ["cargo", "build"],
        ["cargo", "nextest", "run"],
        ["cargo", "test", "--doc"],
        ["cargo", "build", "--examples"],
    ):
        print(f"gate: {' '.join(cmd)}", flush=True)
        run(cmd, cwd=root, env=env)
    readme_cmd = ["python3", str(tools / "readme_check.py"), "--repo", "."]
    name_args = ["--repo-name", repo_name] if repo_name is not None else []
    if entry_json is not None:
        readme_cmd += ["--entry-json", str(entry_json)]
    for cmd in (
        readme_cmd,
        ["python3", str(tools / "doc_refs_check.py"), "--repo", ".", *name_args],
        ["python3", str(tools / "media_check.py"), "--repo", ".", *name_args],
    ):
        print(f"gate: {' '.join(cmd[1:])}", flush=True)
        run(cmd, cwd=root, env=env)


# ---------------------------------------------------------------- dry run


def dry_run(args: argparse.Namespace, mapping: dict[str, str]) -> None:
    target = Path(args.dry_run).expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        fail(f"{target} exists and is not empty")
    if not TEMPLATE_DIR.is_dir():
        fail(f"template not found at {TEMPLATE_DIR}")
    header = Path(args.header).expanduser() if args.header else STAND_IN_HEADER
    if not header.is_file():
        fail(f"no header image at {header}; pass --header PNG")
    shutil.copytree(TEMPLATE_DIR, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*SKIPPED_DIRS))
    substitute(target, mapping)
    shutil.copyfile(header, target / HEADER_PATH)

    entry = {
        "repo": args.crate, "part": args.part, "title": args.title, "pitch": args.pitch,
        "capture_host": "bmb", "subset": args.subset, "hero": HEADER_PATH,
    }
    with tempfile.TemporaryDirectory() as scratch:
        entry_json = Path(scratch) / "entry.json"
        entry_json.write_text(json.dumps(entry))
        run(["python3", str(HERE / "repo_doc.py"), "--repo", str(target), "--entry-json", str(entry_json)])
        run(["git", "init", "-q", "-b", "main"], cwd=target)
        run(["git", "add", "-A"], cwd=target)
        run(["git", *GIT_IDENTITY, "commit", "-q", "-m", "dry run"], cwd=target)
        fill_manifest_sha(target, head_sha(target))
        gate(target, HERE, entry_json, args.crate)
    print(f"dry run passed: {target}")


# ---------------------------------------------------------------- real run


def chapter_index(args: argparse.Namespace, repo_dir: Path) -> str:
    """The book chapter, in the template of DOCUMENTATION.md section 10."""
    crate = args.crate
    pages = []
    for page in sorted((repo_dir / "docs" / "guide").glob("*.md")):
        if page.name == "README.md":
            continue
        title = page.read_text().splitlines()[0].removeprefix("# ").strip()
        pages.append(f"- [{title}](guide/{page.name})")
    return "\n".join([
        f"# {args.title}",
        "",
        f"![{args.chapter_subject}](../../media/chapters/{crate}.png)",
        "",
        f"*{args.title}, in Dark Inc.'s house palette.*",
        "",
        args.pitch,
        "",
        "## Add it",
        "",
        "```sh",
        f"cargo add {crate} --git https://github.com/{ORG}/{crate}",
        "```",
        "",
        "## What it gives you",
        "",
        args.why,
        "",
        "## Use it in the Dark Factory",
        "",
        f"`{pascal_case(crate)}Settings` is the resource the Dark Factory edits for this crate; "
        "the project keeps it in its `family/` folder, so a game configures the crate and never forks it.",
        "",
        "## Guide",
        "",
        *pages,
        "",
        "## Links",
        "",
        f"- [Repository](https://github.com/{ORG}/{crate})",
        f"- [Changelog](https://github.com/{ORG}/{crate}/blob/main/CHANGELOG.md)",
        "- docs.rs: unpublished",
        "",
    ])


def append_chapter_job(wt: Path, args: argparse.Namespace, index: int) -> str:
    """Add `chapter_<crate>` to jobs.json through the art tool's own job builder."""
    spec = importlib.util.spec_from_file_location("dark_inc_art", wt / "art" / "dark_inc_art.py")
    art = importlib.util.module_from_spec(spec)
    sys.modules["dark_inc_art"] = art
    spec.loader.exec_module(art)
    jobs_path = wt / "art" / "jobs.json"
    jobs = load_json(jobs_path)
    job = art.chapter_job(args.crate, index, args.subset, args.chapter_subject)
    jobs.append(job)
    jobs_path.write_text(json.dumps(jobs, indent=1) + "\n")
    return job["id"]


def pick_candidate(art, wt: Path, state: Path, job_id: str, subset: str) -> int:
    jobs = {job["id"]: job for job in load_json(wt / "art" / "jobs.json")}
    job = jobs[job_id]
    colours = art.subset_colours(art.load_palette(), subset)
    from PIL import Image  # local import: only the real run needs Pillow
    for k in range(job["candidates"]):
        candidate = art.candidate_path(state, job, k)
        if not candidate.is_file():
            continue
        ok, _note = art.palette_report(Image.open(candidate), colours)
        if ok:
            return k
    fail("both chapter candidates failed the palette; rerun or edit the prompt")


def real_run(args: argparse.Namespace, mapping: dict[str, str], entries: list[dict]) -> None:
    crate = args.crate
    state = STATE_ROOT / f"new-crate-{crate}"
    state.mkdir(parents=True, exist_ok=True)
    repo_dir = DI / crate
    if repo_dir.exists():
        fail(f"{repo_dir} already exists")

    # 1. the repository, from the template
    run(["gh", "repo", "create", f"{ORG}/{crate}", "--public", "--template", TEMPLATE_REPO, "--clone"], cwd=DI)

    # 2. placeholders
    substitute(repo_dir, mapping)

    # 3. the family's registry, art and profile table, in a worktree of .github
    gh_main = DI / ".github"
    run(["git", "fetch", "-q", "origin"], cwd=gh_main)
    wt = state / "gh"
    run(["git", "worktree", "add", "-q", str(wt), "-b", f"new-crate/{crate}", "origin/main"], cwd=gh_main)
    tools = wt / "tools"
    crates_path = wt / "crates.json"
    registry = load_json(crates_path)
    index = len(registry)
    registry.append({
        "repo": crate, "part": args.part, "title": args.title, "pitch": args.pitch,
        "capture_host": "bmb", "subset": args.subset, "hero": HEADER_PATH,
    })
    crates_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n")
    job_id = append_chapter_job(wt, args, index)
    art_script = wt / "art" / "dark_inc_art.py"
    art_state = state / "art"
    run(["python3", str(art_script), "cost", "--state", str(art_state), "--budget-usd", str(ART_BUDGET_USD)])
    run(["python3", str(art_script), "run", "--state", str(art_state), "--budget-usd", str(ART_BUDGET_USD),
         "--only", job_id])
    art = sys.modules["dark_inc_art"]
    k = pick_candidate(art, wt, art_state, job_id, args.subset)
    run(["python3", str(art_script), "pick", job_id, str(k), "--state", str(art_state)])
    run(["python3", str(tools / "profile_table.py")], cwd=wt)

    # 4. header and the repository's own DOCUMENTATION.md
    shutil.copyfile(wt / "art" / "chapters" / f"{crate}.png", repo_dir / HEADER_PATH)
    run(["python3", str(tools / "repo_doc.py"), "--repo", str(repo_dir)])

    # 5. the gate. Neither GitHub settings nor .github change before it passes.
    fill_manifest_sha(repo_dir, head_sha(repo_dir))
    gate(repo_dir, tools, None, None)

    # 6. first push, then the manifest's real capture commit
    run(["git", "add", "-A"], cwd=repo_dir)
    run(["git", "commit", "-q", "-m", "Initial commit from bevy_crate_template"], cwd=repo_dir)
    run(["git", "push", "origin", "HEAD:main"], cwd=repo_dir)
    fill_manifest_sha(repo_dir, head_sha(repo_dir))
    run(["git", "commit", "-q", "-am", "docs: record the capture commit of the header"], cwd=repo_dir)
    run(["git", "push", "origin", "HEAD:main"], cwd=repo_dir)

    # 7. repository settings
    for label in LABELS:
        run(["gh", "label", "create", label, "--force", "-R", f"{ORG}/{crate}"])
    run(["gh", "api", "-X", "PUT", f"repos/{ORG}/{crate}/actions/permissions/fork-pr-contributor-approval",
         "-f", "approval_policy=all_external_contributors"])
    edit = ["gh", "repo", "edit", f"{ORG}/{crate}", "--description", args.pitch,
            "--homepage", f"https://dark-incorporated.github.io/crates/{crate}/"]
    for topic in REPO_TOPICS:
        edit += ["--add-topic", topic]
    run(edit)

    # 8. CI runner
    repos_txt = RUNNERS_DIR / "repos.txt"
    line = f"{ORG}/{crate} {RUNNER_SLOTS}"
    if line not in repos_txt.read_text().splitlines():
        with repos_txt.open("a") as handle:
            handle.write(line + "\n")
    run([str(RUNNERS_DIR / "deploy.sh"), f"{ORG}/{crate}"])

    # 9. the two pull requests
    run(["git", "add", "crates.json", "art/jobs.json", "art/lock.json", f"art/chapters/{crate}.png",
         "profile/README.md"], cwd=wt)
    run(["git", "commit", "-q", "-m", f"Add {crate} to the family"], cwd=wt)
    run(["git", "push", "-u", "origin", f"new-crate/{crate}"], cwd=wt)
    gh_pr = run(["gh", "pr", "create", "-R", f"{ORG}/.github", "--base", "main", "--head", f"new-crate/{crate}",
                 "--title", f"Add {crate} to the family",
                 "--body", f"Registers {crate} in crates.json, adds its chapter art and the profile table row."],
                capture=True).strip()

    book_main = DI / BOOK_REPO
    run(["git", "fetch", "-q", "origin"], cwd=book_main)
    book = state / "book"
    run(["git", "worktree", "add", "-q", str(book), "-b", f"new-crate/{crate}", "origin/main"], cwd=book_main)
    run(["python3", str(book / "tools" / "sync_crates.py"), "--workspace", str(DI), "--crates", str(crates_path)],
        cwd=book)
    chapter_dir = book / "src" / "crates" / crate
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "index.md").write_text(chapter_index(args, repo_dir))
    media_dir = book / "src" / "media" / "chapters"
    media_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(wt / "art" / "chapters" / f"{crate}.png", media_dir / f"{crate}.png")
    run(["mdbook", "build"], cwd=book)
    run(["git", "add", "-A"], cwd=book)
    run(["git", "commit", "-q", "-m", f"Add the {crate} chapter"], cwd=book)
    run(["git", "push", "-u", "origin", f"new-crate/{crate}"], cwd=book)
    book_pr = run(["gh", "pr", "create", "-R", f"{ORG}/{BOOK_REPO}", "--base", "main", "--head", f"new-crate/{crate}",
                   "--title", f"Add the {crate} chapter",
                   "--body", f"Synced guide pages and the chapter for {crate}."], capture=True).strip()

    # 10. report
    print(f"repository: https://github.com/{ORG}/{crate}")
    print(f".github PR: {gh_pr}")
    print(f"book PR:    {book_pr}")
    print(f"start its loop: WIGGUM_REPO={repo_dir} {LOOP_DRIVER} start")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("crate")
    parser.add_argument("--title", required=True)
    parser.add_argument("--pitch", required=True)
    parser.add_argument("--why", required=True)
    parser.add_argument("--part", required=True)
    parser.add_argument("--subset", required=True)
    parser.add_argument("--chapter-subject", dest="chapter_subject", required=True)
    parser.add_argument("--quality-bar", dest="quality_bar", required=True)
    parser.add_argument("--dry-run", metavar="DIR")
    parser.add_argument("--header", metavar="PNG", help="dry run only: the stand-in header image")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.header and not args.dry_run:
        print("--header is for --dry-run only", file=sys.stderr)
        return 1
    try:
        entries = load_json(CRATES_JSON)
        palette = load_json(PALETTE_JSON)
        validate(args, entries, palette)
        mapping = placeholders(args)
        if args.dry_run:
            dry_run(args, mapping)
        else:
            real_run(args, mapping, entries)
    except Refusal as refusal:
        print(refusal, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
