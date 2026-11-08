# Dark Inc.: what it is and where it is going

> ⚠️ **Vibe Coded.** Dark Inc.'s crates are written by AI agents working from a human's direction, covered by tests rather than a line-by-line human review. Read the code before you rely on it for something you care about.

## The one sentence

**Dark Inc. makes Bevy crates that work alone or together. The Dark Factory is the editor where you and the Night Shift build a game's world, and it ships a blueprint your game loads.**

## The problem

A game developer building a world has two tools that do not talk to each other. The editor is where things get placed; the agent is where the intent lives. Every bridge between them is lossy in the same three ways: **the change has no undo entry, no author, and no validation until a reload.** A person cannot see what the agent did; the agent cannot see what the person did.

Dark Inc.'s answer is one vocabulary. What a person does by hand and what an agent does over MCP are the **same named operations**, over one project file, with one undo history between them. That is why every crate here is built to be driven — by a keyboard, by a script, or by an agent — rather than merely configured.

## Why a dark factory

A lights-out factory runs in the dark because the machines do the work. The person writes the order and inspects what comes out. In the Dark Factory a person sets direction, the Night Shift runs the same named operations (work orders) over MCP, and the operation log records every change.

## The names

The vocabulary is deliberately small, and the words mean one thing each:

|Word|What it is|Replaces|
|---|---|---|
|**Dark Inc.**|the organisation and the family (`github.com/dark-incorporated`)|Bevy Coven|
|**Dark Factory**|the editor (`bevy_dark_factory`)|the Cauldron|
|**the Night Shift**|agents working in the Dark Factory over MCP (`dark_factory_mcp`)|the Familiar|
|**blueprint**|what a game loads: a library of pieces, maps, and the grammar learned from an authored example (`bevy_blueprint`, `blueprint_model`)|the grimoire|
|**work order**|a word for *operation* in docs only; code keeps `operation` and `oplog`|—|

So a game depends on the blueprint; a person builds it in the Dark Factory; and every standalone crate here is a machine the Dark Factory can install. The editor is `bevy_dark_factory`; the runtime is `bevy_blueprint`.

Code and the editor's interface say Bevy's own words: Plugin, Entity, Component, System, Schedule, Resource. The factory words are a way to teach them, used in documents only:

|Factory|Bevy|
|---|---|
|machine|`Plugin` (usually one crate)|
|machine plate|the family API standard ([`STYLE.md`](docs/STYLE.md#the-machine-plate))|
|line|`Schedule`|
|station|`System` (works on every workpiece that has the right parts: a query)|
|workpiece|`Entity`|
|part|`Component`|
|stockroom|`Resource` and assets|

**Install machines (plugins) on the floor; the line (schedule) runs every station (system) over every workpiece (entity) by the parts (components) it carries.**

## The goals

These are the commitments the family is held to. Each is checkable; where it is not, it is a wish and does not belong on this list.

1. **Every crate earns its place alone.** `bevy_flora` grows trees whether or not you run the Dark Factory. A crate that only works inside the editor is a module of the editor, not a crate.
2. **One vocabulary across the human and the agent.** A verb an agent runs is a verb the editor's keymap dispatches. No second path, no key-stroke synthesising.
3. **Engine-free where the engine is not needed.** Data, arithmetic, solvers and the seeded RNG do not link Bevy. `blueprint_model` exists precisely so a server or a test can hold the world model without a renderer, and its `tests/engine_free.rs` fails the build if a `bevy` dependency creeps in.
4. **Games are the consumers, and the seam is an issue.** A game that needs something asks for it as an issue labelled `consumer` and `consumer:<game>`; the general form is built here, proved by a test here, and the game is never named in the API. Neither side reads the other's backlog.
5. **Every visible change ships a picture.** A feature is not done until its README line exists and, if it can be seen, its GIF does — because a family of 14 crates is judged by whether its claims can be checked at a glance.
6. **The record is in the repository.** Logs, research, decisions and post-mortems are committed, not kept in a chat or a wiki, so what was believed at a given commit can be recovered later.
7. **One loop per repository.** Automation is bounded and observable: a loop is a dumb driver rerunning one command, one fresh process per pass, with the repository as its only memory. Nobody is asked to trust an agent's memory.

## The projects

| Project | State | Where |
|---|---|---|
| **The Dark Factory** | the editor; the UI rebuild on `bevy_gooey` is in progress | [`bevy_dark_factory`](https://github.com/dark-incorporated/bevy_dark_factory) (`crates/bevy_dark_factory`) |
| **The blueprint format** | usable; load a library and a map into a running game | [`blueprint_model`](https://github.com/dark-incorporated/bevy_dark_factory) |
| **The world** | nine crates shipped, from sky to crowd | `bevy_elements`, `bevy_flora`, `isomesh`, `bevy_lights`, `bevy_light_grid` |
| **Life** | villagers, marks, steering, dialogue | `bevy_society`, `bevy_stigmergy`, `bevy_orca`, `bevy_speech_bubbles` |
| **Interface** | menus, HUD, dialogs, gamepad navigation | `bevy_gooey` |
| **Spectacle** | fracture, wounds, blood | `bevy_carnage` |
| **Agents and tooling** | an agent driving a running game over MCP | `bevy_fairy` |
| **The book** | the user guide, published | [`dark-incorporated.github.io`](https://github.com/dark-incorporated/dark-incorporated.github.io) |

The authoritative per-crate list, with versions and badges, is the family table in [`profile/README.md`](../profile/README.md). Do not copy it here: it goes stale.

## What Dark Inc. is not

- **Not a game engine.** Bevy is the engine, at one pinned version family-wide ([`ARCHITECTURE.md`](docs/ARCHITECTURE.md)).
- **Not a framework that must be adopted whole.** No crate here requires another to be useful, except where the dependency is the point (the Dark Factory reads a blueprint).
- **Not stable.** Nothing is called stable before `1.0`; the documentation style guide sets `experimental` and `usable` as the only levels below it.

## How this document is kept true

A goal that stops being true is deleted, not softened. When one changes, the commit says why and links the research or the issue that changed it. This file is descriptive of Dark Inc. as it stands and normative about where it is going; the two are separated by tense, and a goal written in the future tense that has no issue behind it is a wish.
