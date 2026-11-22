# How Dark Inc. writes: names, voice and art

The documentation guidance has three layers, and the higher layer wins: this file at the top, [`DOCUMENTATION.md`](DOCUMENTATION.md) in the middle, and a crate's own root `DOCUMENTATION.md` at the bottom.
This file governs names, voice and visuals; `DOCUMENTATION.md` governs structure and checks; a crate's own `DOCUMENTATION.md` adds that repository's facts and nothing else.

Code style is a different document: [`docs/STYLE.md`](docs/STYLE.md) is how Dark Inc. writes Rust, and this file never restates it.

## 1. Names

The vocabulary is deliberately small, and each word means one thing. The canonical name in the table is the only one written anywhere in prose, code, paths or labels; the book's glossary is the only place a former name appears.

|Thing|Canonical|
|---|---|
|the family|Dark Incorporated (short: Dark Inc.), the org `dark-incorporated`|
|the editor|the Dark Factory (the crate `bevy_dark_factory`, the macOS app `DarkFactory.app`)|
|the editor's MCP server|`dark_factory_mcp`|
|the agents working in the editor|the Night Shift|
|what a game loads|a blueprint (the crate `bevy_blueprint`)|
|the book|Dark Incorporated, at `https://dark-incorporated.github.io/`|
|a unit of work an agent runs|a work order, in documents only; code keeps `operation` and `oplog`|

Rules:

- **No other name appears anywhere.** `tools/rename.py --check` enforces this over every tracked file, and it is reported as `FORBIDDEN <file>:<line>: <match>`.
  The patterns it refuses are held in `names.json`, so this guide and the check cannot drift apart.
- **The book's glossary is the only place a former name is written**, because a reader arriving from an old link needs to be told once what the thing is now called.
- **A crate is named for what it does for a game**, never for the product it was extracted from ([`docs/STYLE.md`](docs/STYLE.md)).
- **The editor's name is not a synonym for the family.** Dark Inc. makes the crates; the Dark Factory is one of them.

## 2. Voice and plain words

### Plain words

- Define each term at first use, in a short clause: "ORCA (optimal reciprocal collision avoidance)", "stigmergy (agents coordinating through marks they leave in the world)", "WFC (wave function collapse)", "SDF (signed distance field)".
- Lead with what the reader gets, not how it works.
- Write features as bullets, and identifiers as inline code.
- Research notes stay out of the README; they belong in `docs/research/`.

### Three more rules

- **Plain technical English, and no in-world voice in prose.** The factory vocabulary is a way to teach Bevy's words, used in documents to name a thing, never as a narrator: write "the system runs once per frame", not a line spoken by a machine.
- **The reader is a game developer**, and the agents in the editor are "the Night Shift", never "the AI".
- **British spellings**, as the rest of the docs use: `colour`, `licence`, `behaviour`, `centre`, `normalise`.

## 3. The look

Dark Inc.'s images are gothic industrial machine-cathedral meeting a neon cyberpunk night city, in the manner of an 80s pixel-art adventure game.

### The palette

"Between CGA and VGA" means EGA.
The master set is the 64 EGA colours: every `#RRGGBB` whose channels are each one of `00`, `55`, `AA`, `FF`.
Every generated or scripted image uses at most 16 colours, all drawn from one named subset in [`art/palette.json`](art/palette.json), and palette compliance is measured, not judged.

|Subset|Mood|Hex values|
|---|---|---|
|`night_city`|Neuromancer: rain, neon, CRT|`000000 000055 0000AA 5500AA AA00AA FF00FF FF55FF 550055 005555 00AAAA 00FFFF 55FFFF 555555 AAAAAA FFFFFF 55AAFF`|
|`cathedral`|gothic grime: soot, sodium, rust|`000000 550000 AA0000 FF5555 555500 AA5500 AAAA55 FFFF55 555555 AAAAAA FFFFFF 005500 55AA55 000055 5555AA 550055`|
|`house`|banners, avatar, book: magenta and cyan|`000000 000055 5500AA AA00AA FF55FF 00AAAA 55FFFF 550000 AA0000 AA5500 FFFF55 555555 AAAAAA FFFFFF 005555 FF5555`|

A new piece of art names its subset in `crates.json` (`subset`), so the crate's chapter image and its README hero agree.

### Motif

- Gothic industrial machine-cathedral meets neon cyberpunk night city, in the manner of an 80s adventure game.
- No text, no letters, no logos, no gore, and no named factions or marks belonging to anyone else.
- Rain, grime and CRT glow are the house textures.

### The book theme

The book renders on black with EGA accents; its theme file is `theme/dark-inc.css` in the book repository, overriding the `coal` theme's variables:

|Variable|Value|
|---|---|
|`--bg`|`#000000`|
|`--fg`|`#AAAAAA`|
|`--sidebar-bg`|`#000000`|
|`--sidebar-fg`|`#AAAAAA`|
|`--sidebar-active`|`#55FFFF`|
|`--links`|`#55FFFF`|
|`--inline-code-color`|`#FF55FF`|
|`--theme-hover`|`#000055`|
|`--quote-bg`|`#000055`|
|`--quote-border`|`#5500AA`|
|`--table-header-bg`|`#550055`|
|`--table-alternate-bg`|`#000055`|

Images render pixelated (`img { image-rendering: pixelated; }`), and an `h1` gets an underline in `#AA00AA`.

## 4. Art

Art comes only from [`art/dark_inc_art.py`](art/dark_inc_art.py), which generates it through Retro Diffusion from the jobs in `art/jobs.json`.
Every job except the anchor sends the style anchor, `art/anchor.png`, as a reference image, so the family of images looks like one world.

- **Art regenerates only when its inputs change**: a job is pending when its output is missing or its `inputs_hash` differs from `art/lock.json`, and the hash covers the job JSON, the subset values and the anchor's sha256.
- **A run is capped at $5.00, and a single call at $0.50.** Over budget is a refusal, not a warning.
- **The key is read from `~/.config/retrodiffusion/api_key` and nowhere else.** A missing key stops the run.

### Pick rubric

Candidates are scored 0 to 2 on each of five items, and the highest total wins, ties going to the lowest candidate number:

- **a. Reads at a 64 px thumbnail.** The subject is still legible when shrunk to an icon.
- **b. One subject with a strong silhouette.** One thing, readable as a shape.
- **c. No glyphs, logos or gore.** Nothing that pretends to be text, no brand marks, nothing graphic.
- **d. The motif.** Gothic industrial machine-cathedral in a neon cyberpunk night.
- **e. Palette compliance**, measured: at most 16 colours, every one in the job's subset.

Scripted stills from [`art/diagrams.py`](art/diagrams.py) follow the same subsets, and their README caption says "schematic".

## 5. Captions and alt text

- **Alt text says what happens**, in one sentence, and never merely repeats the caption: "Walkers steer around each other through a gate, then rejoin the path".
- **One italic caption line sits under each image or GIF**, naming the thing and, when it is a piece of art, its palette: `*The Dark Factory, in Dark Inc.'s house palette.*`
- An image with no caption fails the README check (`RC05`): an image nobody explains claims something nobody checked.
