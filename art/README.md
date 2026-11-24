# Org art

The Dark Incorporated avatar, banner, book banner, the style anchor every other
image is drawn against, and one chapter header per crate. All of it comes from
Retro Diffusion through `dark_inc_art.py`; the two crates with nothing to show
get scripted stills from `diagrams.py`. Both draw in the family palette.

The motif is Warhammer 40,000 meets Neuromancer: a gothic industrial
machine-cathedral inside a neon cyberpunk night city, rain, grime, CRT glow, in
the manner of a 1980s pixel-art adventure game. No text, no logos, no gore, and
no Games Workshop marks or named factions.

- `palette.json`: the 64-colour EGA master set and the three 16-colour subsets
  every image is held to. Colours are written as six uppercase hex digits with
  no `#`, so `FF55FF` is magenta.
- `jobs.json`: every generation job, in the order they run.
- `anchor.png`: the style anchor, `art/anchor.png`. Every other job sends it as
  a reference image, so the whole family shares one look.
- `avatar.png` and `banner.png` are copied to `profile/avatar.png` and
  `profile/banner.png`; `book-banner.png` heads the book;
  `chapters/<repo>.png` heads each crate's chapter and its README.
- `lock.json` records which candidate was picked for each job, its seed, its
  cost and the hash of the inputs that produced it. It is written by `pick` and
  committed with the art: without it every job would look never-picked and a
  rerun would regenerate the whole set.

## Palette

"Between CGA and VGA" is EGA: the master set is all 64 colours whose red, green
and blue channels are each one of `00`, `55`, `AA`, `FF`. Every image uses at
most 16 colours, all from one named subset:

|Subset|Mood|Colours|
|---|---|---|
|`night_city`|Neuromancer: neon on wet black|`000000 000055 0000AA 5500AA AA00AA FF00FF FF55FF 550055 005555 00AAAA 00FFFF 55FFFF 555555 AAAAAA FFFFFF 55AAFF`|
|`cathedral`|40k grime: rust, brass, soot|`000000 550000 AA0000 FF5555 555500 AA5500 AAAA55 FFFF55 555555 AAAAAA FFFFFF 005500 55AA55 000055 5555AA 550055`|
|`house`|banners, avatar, book: the Dark Inc. house set|`000000 000055 5500AA AA00AA FF55FF 00AAAA 55FFFF 550000 AA0000 AA5500 FFFF55 555555 AAAAAA FFFFFF 005555 FF5555`|

`house` is the family's own set and carries the org avatar, the banner and the
book; a crate's chapter art takes the subset that suits its subject, and the
anchor is `house`.

## Generating

The key lives at `~/.config/retrodiffusion/api_key` (mode 600). The tool reads
it from there and nowhere else, never prints it, and refuses to run without it:

```sh
python3 art/dark_inc_art.py plan  --state ~/.local/state/dark-inc-docs/art
python3 art/dark_inc_art.py cost  --state ~/.local/state/dark-inc-docs/art --budget-usd 5
python3 art/dark_inc_art.py run   --state ~/.local/state/dark-inc-docs/art --budget-usd 5
python3 art/dark_inc_art.py sheet --state ~/.local/state/dark-inc-docs/art
python3 art/dark_inc_art.py pick  chapter_bevy_orca 1 --state ~/.local/state/dark-inc-docs/art
```

- `plan` lists every job as `pending` or `current` and says why. A job is
  pending when its output is missing, it was never picked, or the hash of its
  inputs changed. The hash covers the job's own JSON, its subset's colours and
  the sha256 of `anchor.png`; if the anchor is pending, every job is pending.
- `cost` prices every pending candidate with the API's free `check_cost` call
  and prints a total per job. It charges nothing. A whole run is about $2.90:
  13 `rd_core` candidates at $0.10 and 32 `rd_lite` candidates at $0.05.
- `run` generates candidates into `STATE/art/<id>/cand-<k>.png`, anchor first.
  It refuses a single call over $0.50 and a run over `--budget-usd` (default
  $5.00), and it will not run the rest until the anchor has been picked. Each
  candidate is measured against its subset at native size and reported
  `palette_fail` when it strays.
- `sheet` writes `STATE/art/<id>/sheet.png`, the contact sheet each pick is made
  from.
- `pick ID K` scales candidate `K` to its output size with NEAREST, writes it,
  copies it to the job's `copy_to` targets, and records the pick in `lock.json`.
  A candidate that fails the palette is refused.

The style anchor is the first thing to generate: the rest use it as a reference
image, so the family reads as one set. A paid call is preceded by a free price
check and carries a fresh `Idempotency-Key`; a task that failed is never
resubmitted. A run that loses the network keeps the key, so re-running asks for
the same task rather than paying twice.

## Picking

Each candidate scores 0-2 on five criteria, 10 in all:

- **a**: reads at a 64 px thumbnail;
- **b**: one subject with a strong silhouette;
- **c**: no glyphs, logos or gore;
- **d**: the motif — the machine-cathedral, the night city, rain, CRT glow;
- **e**: palette compliance, measured.

The highest total wins; a tie goes to the lower candidate number. The scores and
the winner go in the run's `REPORT.md`. When a person is available they pick
instead, from the same sheets.

## Scripted stills

`bevy_devshot` and `bevy_light_grid` have no visual output to photograph, so
their README hero is a diagram:

```sh
python3 art/diagrams.py devshot    --out ../bevy_devshot/docs/media/hero.png
python3 art/diagrams.py light_grid --out ../bevy_light_grid/docs/media/hero.png
```

`devshot` shows a terminal asking for a screenshot, the game window and the
written `screenshot.png`, joined by arrows. `light_grid` shows a 32×18 cell grid
lit by two lamps, with one wall casting a hard shadow. Both are drawn in
`night_city`, use at most 16 colours, and are captioned "schematic" in the crate
README because they show what the crate does, not a screenshot of it.

The fix-loop walkthrough (`docs/fix-loop.md`) has three figures from one script,
drawn over real captures in the `house` palette:

```sh
python3 art/fix_loop_figure.py                          # write art/fix-loop-*.png
python3 art/fix_loop_figure.py --out /tmp/check --check # measure them instead
```

`editor` boxes five things on a capture of the editor, `proof` shows one fix's
before and after, and `flow` is a schematic. The captures are in
`art/sources/`, and the script's docstring says where each came from. `--check`
fails on a colour outside the subset, a label or leader over the interface,
sources that disagree, or a figure that differs from the committed one.

## Formerly

Before 2026-11-21 this directory held two earlier sets, both kept under
`archive/`:

- Rounds 1 to 4 of the family's pre-Dark-Inc. art — a raven against a moon, a
  witch and a castle — live beside `archive/round5/`, generated on big with the
  local Retro Diffusion SD 1.5 checkpoints through `dark_art.py`, with the job
  files and contact sheets that produced them.
- `archive/round5/` holds the 2026-11-08 Dark Inc. round: four RD Pro jobs
  (`rd_api.py`, `rd-jobs-dark-inc.json`) that made the technomancer avatar, the
  smokestack banner, the robotic-arm app icon and the splash, at $0.18 an image.

`archive/` keeps the names it was written with, because its job files must still
reproduce the images they made; the rename check skips that tree for the same
reason. `archive/README.md` is the old README verbatim, including the per-round
score tables and the API notes, so those runs can still be checked and repeated.
