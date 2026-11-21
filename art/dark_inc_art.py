#!/usr/bin/env python3
"""Dark Inc. org art: Retro Diffusion v2 (https://www.retrodiffusion.ai/app/guide/api).

Every job in ``jobs.json`` is priced free (``check_cost: true``) before it is
paid for, and a single call above ``MAX_USD_PER_CALL`` is refused. A paid
generation posts to ``/inferences`` with a fresh ``Idempotency-Key`` (written to
the job's state directory first, so an uncertain admission can be recovered by
the same key), then polls ``GET /inferences/tasks/{id}`` every
``POLL_INTERVAL_S`` until the task settles or ``TASK_TIMEOUT_S`` passes. A task
that failed is never resubmitted: the caller decides whether to pay again.

The key is read from ``~/.config/retrodiffusion/api_key`` and from nowhere
else. It is never printed, and never written into a job, a state file or a log.

Subcommands::

    plan  --state DIR
    cost  --state DIR --budget-usd 5
    run   --state DIR --budget-usd 5 [--only ID ...]
    sheet --state DIR
    pick  ID K --state DIR

``--api-base`` is for this tool's own test against a local fake server; a real
run never passes it.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ART_DIR = Path(__file__).resolve().parent
REPO_ROOT = ART_DIR.parent
PALETTE_FILE = ART_DIR / "palette.json"
JOBS_FILE = ART_DIR / "jobs.json"
LOCK_FILE = ART_DIR / "lock.json"

API_BASE_DEFAULT = "https://api.retrodiffusion.ai/v2"
KEY_PATH = Path("~/.config/retrodiffusion/api_key")
DEFAULT_BUDGET_USD = 5.0
MAX_USD_PER_CALL = 0.50

POLL_INTERVAL_S = 2.0
TASK_TIMEOUT_S = 180.0
REQUEST_TIMEOUT_S = 60.0
DEFAULT_RETRY_AFTER_S = 5.0
MAX_RATE_LIMIT_RETRIES = 3

MAX_COLOURS = 16
SHEET_BG = (0, 0, 0)
SHEET_LABEL_COLOUR = (255, 255, 255)
SHEET_COLUMNS = 2
SHEET_GAP_PX = 6
SHEET_VIEW_H_PX = 192

ANCHOR_ID = "anchor"
ANCHOR_OUT = "art/anchor.png"

# Every prompt in jobs.json ends with this. The anchor is the style reference:
# a subject first, then the motif, then the exclusions Retro Diffusion would
# otherwise happily draw (glyphs, logos, gore).
SHARED_PROMPT_SUFFIX = (
    ", 1980s pixel art adventure game, gothic industrial machine cathedral meets neon "
    "cyberpunk night city, rain, grime, CRT glow, no text, no letters, no logos, no gore"
)
CHAPTER_STYLE = "rd_lite__scifi"
CHAPTER_WIDTH = 384
CHAPTER_HEIGHT = 96
CHAPTER_UPSCALE = 2
CHAPTER_CANDIDATES = 2
CHAPTER_SEED_BASE = 2000
CHAPTER_SEED_STEP = 10

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_NO_KEY = 2
EXIT_OVER_BUDGET = 4

_PENDING_STATUSES = frozenset({"accepted", "pending", "running"})


class ArtError(Exception):
    """A refusal or a failed call, reported on stderr with an exit code."""

    def __init__(self, message: str, code: int = EXIT_FAILED) -> None:
        super().__init__(message)
        self.code = code


class SettledFailureError(ArtError):
    """The task finished as failed; it is never resubmitted, by this tool or a re-run."""


class UncertainError(ArtError):
    """The task may have been accepted and charged; a re-run recovers it for free.

    The job's Idempotency-Key is kept on disk, so the next ``run`` sends the same
    key and the API answers the same task rather than charging a new one.
    """


# -- configuration -----------------------------------------------------------


def _ssl_context() -> ssl.SSLContext:
    """A verified context; this machine's python.org build ships no CA bundle."""
    try:
        import certifi  # noqa: PLC0415 - optional, only supplies a CA file
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def load_palette() -> dict[str, Any]:
    try:
        data = json.loads(PALETTE_FILE.read_text())
    except FileNotFoundError:
        raise ArtError(f"no palette at {PALETTE_FILE}") from None
    except json.JSONDecodeError as error:
        raise ArtError(f"{PALETTE_FILE} is not JSON: {error}") from None
    if not isinstance(data, dict) or "master" not in data or "subsets" not in data:
        raise ArtError(f"{PALETTE_FILE} needs 'master' and 'subsets'")
    return data


def chapter_job(repo: str, index: int, subset: str, subject: str) -> dict[str, Any]:
    """The ``chapter_<repo>`` job exactly as jobs.json stores it.

    ``index`` is the crate's 0-based place in ``crates.json``; it alone decides
    the seed, so a reordering of the family reseeds the chapters that moved.
    """
    return {
        "id": f"chapter_{repo}",
        "prompt_style": CHAPTER_STYLE,
        "width": CHAPTER_WIDTH,
        "height": CHAPTER_HEIGHT,
        "upscale": CHAPTER_UPSCALE,
        "subset": subset,
        "seed": CHAPTER_SEED_BASE + index * CHAPTER_SEED_STEP,
        "candidates": CHAPTER_CANDIDATES,
        "prompt": subject + SHARED_PROMPT_SUFFIX,
        "out": f"art/chapters/{repo}.png",
        "copy_to": [],
    }


def load_jobs() -> list[dict[str, Any]]:
    try:
        jobs = json.loads(JOBS_FILE.read_text())
    except FileNotFoundError:
        raise ArtError(f"no job list at {JOBS_FILE}") from None
    except json.JSONDecodeError as error:
        raise ArtError(f"{JOBS_FILE} is not JSON: {error}") from None
    if not isinstance(jobs, list) or not jobs:
        raise ArtError(f"{JOBS_FILE} must be a non-empty list")
    required = {"id", "prompt_style", "width", "height", "upscale", "subset", "seed",
                "candidates", "prompt", "out"}
    seen: set[str] = set()
    for job in jobs:
        missing = required - set(job)
        if missing:
            raise ArtError(f"job {job.get('id')!r} is missing {', '.join(sorted(missing))}")
        if job["id"] in seen:
            raise ArtError(f"job id {job['id']!r} appears twice")
        seen.add(job["id"])
    if jobs[0]["id"] != ANCHOR_ID:
        raise ArtError(f"the first job must be {ANCHOR_ID!r}")
    return jobs


def job_by_id(jobs: list[dict[str, Any]], job_id: str) -> dict[str, Any]:
    for job in jobs:
        if job["id"] == job_id:
            return job
    raise ArtError(f"no job {job_id!r} in {JOBS_FILE}")


def subset_colours(palette: dict[str, Any], name: str) -> tuple[str, ...]:
    subsets = palette["subsets"]
    if name not in subsets:
        raise ArtError(f"no palette subset {name!r}; known: {', '.join(sorted(subsets))}")
    colours = tuple(str(c).upper() for c in subsets[name])
    outside = [c for c in colours if c not in palette["master"]]
    if outside:
        raise ArtError(f"subset {name!r} has colours outside the master palette: {outside}")
    return colours


def read_api_key() -> str:
    path = KEY_PATH.expanduser()
    try:
        key = path.read_text().strip()
    except FileNotFoundError:
        raise ArtError(f"no Retro Diffusion key at {KEY_PATH}", EXIT_NO_KEY) from None
    if not key:
        raise ArtError(f"no Retro Diffusion key at {KEY_PATH}", EXIT_NO_KEY)
    return key


# -- state and hashing -------------------------------------------------------


def state_art_dir(state: Path, job: dict[str, Any]) -> Path:
    path = state / "art" / job["id"]
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_lock() -> dict[str, Any]:
    try:
        data = json.loads(LOCK_FILE.read_text())
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as error:
        raise ArtError(f"{LOCK_FILE} is not JSON: {error}") from None
    if not isinstance(data, dict):
        raise ArtError(f"{LOCK_FILE} must be an object keyed by job id")
    return data


def write_lock(lock: dict[str, Any]) -> None:
    LOCK_FILE.write_text(json.dumps(lock, indent=1, sort_keys=True) + "\n")


def anchor_sha() -> str | None:
    path = REPO_ROOT / ANCHOR_OUT
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs_hash(job: dict[str, Any], palette: dict[str, Any]) -> str:
    """sha256 of the job JSON, its subset's colours and (except anchor) anchor.png."""
    material = {
        "job": job,
        "subset_values": list(subset_colours(palette, job["subset"])),
    }
    if job["id"] != ANCHOR_ID:
        anchor = anchor_sha()
        if anchor is None:
            raise ArtError(f"{ANCHOR_OUT} is missing, so {job['id']!r} has no style anchor")
        material["anchor_sha256"] = anchor
    blob = json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def pending_jobs(
    jobs: list[dict[str, Any]], palette: dict[str, Any], lock: dict[str, Any]
) -> list[tuple[dict[str, Any], str]]:
    """Every job that must be (re)generated, with the reason it is pending."""
    reasons: dict[str, str] = {}
    anchor_job = jobs[0]
    anchor_pending = not (REPO_ROOT / ANCHOR_OUT).exists()
    if not anchor_pending:
        entry = lock.get(ANCHOR_ID)
        if entry is None:
            anchor_pending = True
        elif entry.get("inputs_hash") != inputs_hash(anchor_job, palette):
            anchor_pending = True
    if anchor_pending:
        reasons[ANCHOR_ID] = "anchor missing or its inputs changed"
        for job in jobs[1:]:
            reasons[job["id"]] = "anchor is pending"
        return [(job, reasons[job["id"]]) for job in jobs]

    for job in jobs:
        entry = lock.get(job["id"])
        out = REPO_ROOT / job["out"]
        if not out.exists():
            reasons[job["id"]] = f"{job['out']} missing"
        elif entry is None:
            reasons[job["id"]] = "never picked"
        elif entry.get("inputs_hash") != inputs_hash(job, palette):
            reasons[job["id"]] = "inputs changed"
    return [(job, reasons[job["id"]]) for job in jobs if job["id"] in reasons]


# -- palette PNG -------------------------------------------------------------


def palette_png_base64(colours: tuple[str, ...]) -> str:
    """A 1xN PNG with one pixel per palette colour, as raw base64."""
    pixels = []
    for entry in colours:
        digits = entry.lstrip("#").upper()
        if len(digits) != 6:
            raise ArtError(f"palette colour {entry!r} is not 6 hex digits")
        pixels.append(tuple(int(digits[i : i + 2], 16) for i in (0, 2, 4)))
    image = Image.new("RGB", (len(pixels), 1))
    image.putdata(pixels)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def palette_report(image: Image.Image, colours: tuple[str, ...]) -> tuple[bool, str]:
    """Does every pixel use one of ``colours``, and at most MAX_COLOURS of them?"""
    rgb = image.convert("RGB")
    used = {f"{r:02X}{g:02X}{b:02X}" for _, (r, g, b) in rgb.getcolors(maxcolors=1 << 24) or []}
    outside = sorted(used - set(colours))
    if outside:
        return False, f"{len(outside)} colours outside the subset, e.g. {outside[:4]}"
    if len(used) > MAX_COLOURS:
        return False, f"{len(used)} colours > {MAX_COLOURS}"
    return True, f"{len(used)} colours inside the subset"


# -- HTTP --------------------------------------------------------------------


def _error_text(body: bytes) -> str:
    try:
        parsed = json.loads(body)
    except ValueError:
        return body.decode("utf-8", "replace")[:300]
    if isinstance(parsed, dict):
        error = parsed.get("error")
        if isinstance(error, dict):
            code, message = error.get("code"), error.get("message")
            return f"{code}: {message}" if code else str(message)
        if "detail" in parsed:
            return str(parsed["detail"])[:300]
    return str(parsed)[:300]


class Client:
    def __init__(self, api_base: str, key: str) -> None:
        self._api_base = api_base.rstrip("/")
        self._key = key
        self._context = _ssl_context()

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None,
        idem: str | None,
        *,
        uncertain: bool,
    ) -> dict[str, Any]:
        headers = {"X-RD-Token": self._key, "Content-Type": "application/json"}
        if idem:
            headers["Idempotency-Key"] = idem
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            f"{self._api_base}{path}", data=data, headers=headers, method=method
        )
        for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
            try:
                with urllib.request.urlopen(
                    request, timeout=REQUEST_TIMEOUT_S, context=self._context
                ) as response:
                    raw = response.read()
                break
            except urllib.error.HTTPError as error:
                if error.code != 429 or attempt == MAX_RATE_LIMIT_RETRIES:
                    raise ArtError(
                        f"Retro Diffusion HTTP {error.code}: {_error_text(error.read())}"
                    ) from None
                try:
                    wait_s = float(error.headers.get("Retry-After", DEFAULT_RETRY_AFTER_S))
                except (TypeError, ValueError):
                    wait_s = DEFAULT_RETRY_AFTER_S
                time.sleep(wait_s)
            except urllib.error.URLError as error:
                paid = (
                    "; the request may have been accepted and charged"
                    if uncertain
                    else ""
                )
                raise UncertainError(
                    f"Retro Diffusion unreachable ({error.reason}){paid}"
                ) from None
        try:
            parsed = json.loads(raw)
        except ValueError:
            raise ArtError(f"Retro Diffusion returned non-JSON: {raw[:200]!r}") from None
        if not isinstance(parsed, dict):
            raise ArtError(f"Retro Diffusion returned {type(parsed).__name__}, expected an object")
        return parsed

    def get(self, path: str) -> dict[str, Any]:
        return self._request("GET", path, None, None, uncertain=False)

    def post(self, body: dict[str, Any], idem: str | None) -> dict[str, Any]:
        """A priced request is retried on HTTP 429 under the same Idempotency-Key.

        The key is what makes the retry free of double charges: the API answers
        the task the first attempt already admitted rather than starting another.
        """
        return self._request(
            "POST", "/inferences", body, idem, uncertain=idem is not None
        )

    def cost(self, payload: dict[str, Any]) -> float:
        body = self.post({**payload, "check_cost": True}, None)
        if "task_id" in body:
            body = self.poll(str(body["task_id"]))
        if "balance_cost" not in body:
            raise ArtError(f"cost check returned no balance_cost: {sorted(body)}")
        return float(body["balance_cost"])

    def poll(self, task_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + TASK_TIMEOUT_S
        while True:
            task = self.get(f"/inferences/tasks/{task_id}")
            status = task.get("status")
            if status == "succeeded":
                result = task.get("result")
                if not isinstance(result, dict):
                    raise ArtError(f"task {task_id} succeeded without a result")
                return result
            if status == "failed":
                error = task.get("error")
                text = (
                    f"{error.get('code')}: {error.get('message')}"
                    if isinstance(error, dict)
                    else "no error detail"
                )
                raise SettledFailureError(f"task {task_id} failed: {text}")
            if status not in _PENDING_STATUSES:
                raise ArtError(f"task {task_id} has status {status!r}")
            if time.monotonic() >= deadline:
                raise UncertainError(
                    f"task {task_id} still {status} after {TASK_TIMEOUT_S:.0f} s; "
                    "it may still complete and be charged"
                )
            time.sleep(POLL_INTERVAL_S)


# -- payloads ----------------------------------------------------------------


def job_payload(
    job: dict[str, Any], palette: dict[str, Any], reference_png: bytes | None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "prompt": job["prompt"],
        "prompt_style": job["prompt_style"],
        "width": job["width"],
        "height": job["height"],
        "num_images": 1,
        "seed": job["seed"],
        "upscale_output_factor": job["upscale"],
        "input_palette": palette_png_base64(subset_colours(palette, job["subset"])),
    }
    if reference_png is not None:
        payload["reference_images"] = [base64.b64encode(reference_png).decode("ascii")]
    return payload


def candidate_path(state: Path, job: dict[str, Any], index: int) -> Path:
    return state / "art" / job["id"] / f"cand-{index}.png"


def native_palette_report(
    path: Path, job: dict[str, Any], colours: tuple[str, ...]
) -> tuple[bool, str]:
    """Measure a candidate at its native size, where the palette actually lives.

    Retro Diffusion may already have upscaled it by ``upscale``; dividing back
    with NEAREST keeps the pixel grid, so a colour measured here is the colour
    the model chose rather than an interpolation the upscaler invented.
    """
    native_size = (job["width"], job["height"])
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        if rgb.size == native_size:
            return palette_report(rgb, colours)
        if rgb.width % native_size[0] == 0 and rgb.height % native_size[1] == 0:
            return palette_report(rgb.resize(native_size, Image.NEAREST), colours)
    return palette_report(rgb, colours)


# -- commands ----------------------------------------------------------------


def cmd_plan(args: argparse.Namespace) -> int:
    palette = load_palette()
    jobs = load_jobs()
    lock = read_lock()
    pending = pending_jobs(jobs, palette, lock)
    pending_ids = {job["id"]: reason for job, reason in pending}
    for job in jobs:
        if job["id"] in pending_ids:
            state, reason = "pending", pending_ids[job["id"]]
        else:
            state, reason = "current", f"picked candidate {lock[job['id']]['k']}"
        print(f"{job['id']:<32} {state:<8} {reason}")
    print(f"{len(pending_ids)} of {len(jobs)} jobs pending")
    return EXIT_OK


def cmd_cost(args: argparse.Namespace) -> int:
    palette = load_palette()
    jobs = load_jobs()
    lock = read_lock()
    pending = pending_jobs(jobs, palette, lock)
    client = Client(args.api_base, read_api_key())
    anchor_path = REPO_ROOT / ANCHOR_OUT
    reference = anchor_path.read_bytes() if anchor_path.exists() else None
    total = 0.0
    if reference is None and any(job["id"] != ANCHOR_ID for job, _ in pending):
        print(
            f"note: {ANCHOR_OUT} does not exist yet; other jobs are priced without a "
            "reference image (Retro Diffusion charges the same)",
            file=sys.stderr,
        )
    for job, _reason in pending:
        payload = job_payload(job, palette, None if job["id"] == ANCHOR_ID else reference)
        try:
            price = client.cost(payload)
        except ArtError as error:
            raise ArtError(f"{job['id']}: {error}") from None
        if price > MAX_USD_PER_CALL:
            raise ArtError(
                f"{job['id']}: ${price:.2f} for one image exceeds the "
                f"${MAX_USD_PER_CALL:.2f} per-call cap"
            )
        job_total = price * job["candidates"]
        total += job_total
        print(f"{job['id']:<32} {job['prompt_style']:<18} "
              f"{job['candidates']} x ${price:.2f} = ${job_total:.2f}")
    print(f"total ${total:.2f} for {sum(j['candidates'] for j, _ in pending)} candidates")
    if args.budget_usd is not None and total > args.budget_usd:
        raise ArtError(
            f"over budget: ${total:.2f} > ${args.budget_usd:.2f}", EXIT_OVER_BUDGET
        )
    return EXIT_OK


def _generate_candidate(
    client: Client, job: dict[str, Any], payload: dict[str, Any], index: int, state: Path
) -> float:
    job_dir = state_art_dir(state, job)
    out = candidate_path(state, job, index)
    failed_marker = job_dir / f"cand-{index}.failed"
    if failed_marker.exists():
        raise ArtError(
            f"{job['id']} candidate {index} failed earlier "
            f"({failed_marker.read_text().strip()}); not resubmitting"
        )
    idem_file = job_dir / f"cand-{index}.idem"
    idem = idem_file.read_text().strip() if idem_file.exists() else ""
    if not idem:
        idem = str(uuid.uuid4())
        idem_file.write_text(idem + "\n")

    price = client.cost(payload)
    if price > MAX_USD_PER_CALL:
        raise ArtError(
            f"{job['id']}: ${price:.2f} for one image exceeds the "
            f"${MAX_USD_PER_CALL:.2f} per-call cap; nothing was generated"
        )
    accepted = client.post(payload, idem)
    task_id = str(accepted["task_id"]) if "task_id" in accepted else None
    try:
        result = client.poll(task_id) if task_id else accepted
    except SettledFailureError as error:
        failed_marker.write_text(f"{task_id or 'no task'}: {error}\n")
        idem_file.unlink(missing_ok=True)
        raise
    except UncertainError as error:
        raise UncertainError(
            f"{error}; its Idempotency-Key stays on disk, so a re-run asks for the "
            "same task instead of starting a new one"
        ) from None
    images = result.get("base64_images") or []
    if images:
        png = base64.b64decode(images[0])
    else:
        urls = result.get("output_urls") or []
        if not urls:
            raise UncertainError(
                f"{job['id']}: the result has no base64_images or output_urls; the task "
                "was charged and its Idempotency-Key stays on disk"
            )
        try:
            with urllib.request.urlopen(urls[0], timeout=REQUEST_TIMEOUT_S) as download:
                png = download.read()
        except (urllib.error.URLError, urllib.error.HTTPError) as error:
            raise UncertainError(
                f"{job['id']}: downloading the image failed ({error}); the task was "
                "charged and its Idempotency-Key stays on disk"
            ) from None
    out.write_bytes(png)
    charged = float(result.get("balance_cost", price))
    idem_file.unlink(missing_ok=True)
    (job_dir / f"cand-{index}.json").write_text(
        json.dumps({"task_id": task_id, "cost_usd": charged, "seed": job["seed"]},
                   indent=1) + "\n"
    )
    return charged


def _record_palette(
    state: Path, job: dict[str, Any], index: int, ok: bool, note: str
) -> None:
    """Keep the palette verdict beside the candidate, so a pick can cite it."""
    meta_file = state / "art" / job["id"] / f"cand-{index}.json"
    meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
    meta["palette_ok"] = ok
    meta["palette_note"] = note
    meta_file.write_text(json.dumps(meta, indent=1) + "\n")


def cmd_run(args: argparse.Namespace) -> int:
    palette = load_palette()
    jobs = load_jobs()
    lock = read_lock()
    state = Path(args.state).expanduser().resolve()
    state.mkdir(parents=True, exist_ok=True)
    pending = pending_jobs(jobs, palette, lock)
    pending_ids = {job["id"] for job, _ in pending}
    wanted = set(args.only) if args.only else None
    if wanted is not None:
        unknown = wanted - {job["id"] for job in jobs}
        if unknown:
            raise ArtError(f"no job(s) {', '.join(sorted(unknown))} in {JOBS_FILE}")

    anchor_pending = ANCHOR_ID in pending_ids
    if anchor_pending and (wanted is None or ANCHOR_ID not in wanted):
        raise ArtError(
            "the style anchor is pending: run `run --only anchor`, pick a candidate "
            "with `pick anchor K`, then run the rest"
        )
    if anchor_pending:
        job = jobs[0]
        client = Client(args.api_base, read_api_key())
        payload = job_payload(job, palette, None)
        price = client.cost(payload)
        planned = price * job["candidates"]
        if price > MAX_USD_PER_CALL:
            raise ArtError(
                f"{job['id']}: ${price:.2f} for one image exceeds the "
                f"${MAX_USD_PER_CALL:.2f} per-call cap; nothing was generated"
            )
        if planned > args.budget_usd:
            raise ArtError(
                f"over budget: ${planned:.2f} > ${args.budget_usd:.2f}", EXIT_OVER_BUDGET
            )
        print(f"{job['id']}: generating {job['candidates']} candidates (${planned:.2f})")
        spent = 0.0
        for index in range(job["candidates"]):
            out = candidate_path(state, job, index)
            if out.exists():
                print(f"  cand-{index}: already there")
                continue
            spent += _generate_candidate(client, job, payload, index, state)
            ok, note = native_palette_report(out, job, subset_colours(palette, job["subset"]))
            _record_palette(state, job, index, ok, note)
            print(f"  cand-{index}: ${spent:.2f} so far, "
                  f"{'palette ok' if ok else 'palette_fail'} ({note})")
        print("now: python3 art/dark_inc_art.py sheet --state "
              f"{state} && pick {job['id']} K --state {state}")
        return EXIT_OK

    anchor_png = (REPO_ROOT / ANCHOR_OUT).read_bytes()
    selected = [
        job for job, reason in pending if wanted is None or job["id"] in wanted
    ]
    if not selected:
        print("nothing pending")
        return EXIT_OK
    client = Client(args.api_base, read_api_key())
    total = 0.0
    for job in selected:
        payload = job_payload(job, palette, anchor_png)
        prices = [client.cost(payload)] * job["candidates"]
        if any(price > MAX_USD_PER_CALL for price in prices):
            raise ArtError(
                f"{job['id']}: one image exceeds ${MAX_USD_PER_CALL:.2f}; nothing generated"
            )
        planned = sum(prices)
        if total + planned > args.budget_usd:
            raise ArtError(
                f"over budget: ${total + planned:.2f} > ${args.budget_usd:.2f}", EXIT_OVER_BUDGET
            )
        print(f"{job['id']}: generating {job['candidates']} candidates (${planned:.2f})")
        for index in range(job["candidates"]):
            out = candidate_path(state, job, index)
            if out.exists():
                print(f"  cand-{index}: already there")
                continue
            total += _generate_candidate(client, job, payload, index, state)
            ok, note = native_palette_report(out, job, subset_colours(palette, job["subset"]))
            _record_palette(state, job, index, ok, note)
            print(f"  cand-{index}: ${total:.2f} so far, "
                  f"{'palette ok' if ok else 'palette_fail'} ({note})")
    print(f"spent ${total:.2f}")
    return EXIT_OK


def cmd_sheet(args: argparse.Namespace) -> int:
    state = Path(args.state).expanduser().resolve()
    jobs = load_jobs()
    written = 0
    for job in jobs:
        candidates = sorted(
            (state / "art" / job["id"]).glob("cand-*.png"),
            key=lambda path: int(path.stem.split("-")[1]),
        )
        if not candidates:
            continue
        thumbs = []
        font = ImageFont.load_default()
        for path in candidates:
            with Image.open(path) as image:
                thumb = image.convert("RGB")
                # Divide by the largest whole factor that both axes accept, so the
                # sheet shows the candidate's own pixel grid and no interpolation.
                factor = 1
                for candidate in range(int(thumb.height // SHEET_VIEW_H_PX), 1, -1):
                    if thumb.width % candidate == 0 and thumb.height % candidate == 0:
                        factor = candidate
                        break
                if factor > 1:
                    thumb = thumb.resize(
                        (thumb.width // factor, thumb.height // factor), Image.NEAREST
                    )
            label = path.stem.split("-")[1]
            strip = Image.new("RGB", (thumb.width, thumb.height + 12), SHEET_BG)
            strip.paste(thumb, (0, 12))
            ImageDraw.Draw(strip).text((2, 1), label, fill=SHEET_LABEL_COLOUR, font=font)
            thumbs.append(strip)
        columns = min(SHEET_COLUMNS, len(thumbs))
        rows = (len(thumbs) + columns - 1) // columns
        cell_w = max(t.width for t in thumbs)
        cell_h = max(t.height for t in thumbs)
        sheet = Image.new(
            "RGB",
            (columns * cell_w + (columns + 1) * SHEET_GAP_PX,
             rows * cell_h + (rows + 1) * SHEET_GAP_PX),
            SHEET_BG,
        )
        for index, thumb in enumerate(thumbs):
            x = SHEET_GAP_PX + (index % columns) * (cell_w + SHEET_GAP_PX)
            y = SHEET_GAP_PX + (index // columns) * (cell_h + SHEET_GAP_PX)
            sheet.paste(thumb, (x, y))
        out = state / "art" / job["id"] / "sheet.png"
        sheet.save(out)
        print(f"{job['id']}: {out} ({len(thumbs)} candidates)")
        written += 1
    if not written:
        raise ArtError(f"no candidates under {state / 'art'}")
    return EXIT_OK


def cmd_pick(args: argparse.Namespace) -> int:
    state = Path(args.state).expanduser().resolve()
    palette = load_palette()
    jobs = load_jobs()
    job = job_by_id(jobs, args.id)
    colours = subset_colours(palette, job["subset"])
    source = candidate_path(state, job, args.k)
    if not source.exists():
        raise ArtError(f"no candidate {args.k} for {job['id']} at {source}")
    ok, note = native_palette_report(source, job, colours)
    if not ok:
        raise ArtError(
            f"{source} fails the palette at {job['width']}x{job['height']}: {note}"
        )
    target_size = (job["width"] * job["upscale"], job["height"] * job["upscale"])
    with Image.open(source) as image:
        picked = image.convert("RGB").resize(target_size, Image.NEAREST)
    out = REPO_ROOT / job["out"]
    out.parent.mkdir(parents=True, exist_ok=True)
    picked.save(out)
    for copy in job.get("copy_to") or []:
        destination = REPO_ROOT / copy
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(out.read_bytes())
        print(f"copied {job['out']} -> {copy}")
    meta_file = state / "art" / job["id"] / f"cand-{args.k}.json"
    charged = 0.0
    if meta_file.exists():
        charged = float(json.loads(meta_file.read_text()).get("cost_usd", 0.0))
    lock = read_lock()
    entry = {
        "id": job["id"],
        "inputs_hash": inputs_hash(job, palette),
        "seed": job["seed"],
        "k": args.k,
        "cost_usd": charged,
        "picked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    lock[job["id"]] = entry
    write_lock(lock)
    print(f"picked {job['id']} candidate {args.k} -> {job['out']} ({picked.width}x{picked.height})")
    return EXIT_OK


# -- CLI ---------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--api-base", default=API_BASE_DEFAULT, help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="which jobs are pending, and why")
    plan.add_argument("--state", required=True)
    plan.set_defaults(func=cmd_plan)

    cost = sub.add_parser("cost", help="price every pending candidate (free)")
    cost.add_argument("--state", required=True)
    cost.add_argument("--budget-usd", type=float, default=None)
    cost.set_defaults(func=cmd_cost)

    run = sub.add_parser("run", help="generate candidates")
    run.add_argument("--state", required=True)
    run.add_argument("--budget-usd", type=float, default=DEFAULT_BUDGET_USD)
    run.add_argument("--only", nargs="+", metavar="ID")
    run.set_defaults(func=cmd_run)

    sheet = sub.add_parser("sheet", help="one contact sheet per job")
    sheet.add_argument("--state", required=True)
    sheet.set_defaults(func=cmd_sheet)

    pick = sub.add_parser("pick", help="scale a candidate to its output and record it")
    pick.add_argument("id")
    pick.add_argument("k", type=int)
    pick.add_argument("--state", required=True)
    pick.set_defaults(func=cmd_pick)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ArtError as error:
        print(str(error), file=sys.stderr)
        return error.code
    except KeyError as error:
        print(f"unexpected response shape: missing {error}", file=sys.stderr)
        return EXIT_FAILED


if __name__ == "__main__":
    raise SystemExit(main())
