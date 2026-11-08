![Dark Inc.: a vast dark factory at night seen from the wet street, smokestacks and steam, one amber-lit window, a giant robotic arm against a neon-magenta sky, in pixel art](banner.png)

# Dark Inc.

**Lights out. The machines are working.**

Dark Inc. makes Bevy crates that work alone or together. The Dark Factory is the editor where you and the Night Shift build a game's world, and it ships a blueprint your game loads.

> ⚠️ **Vibe Coded.** Written by AI agents working from a human's direction, covered by tests rather than a line-by-line human review. Read the code before you rely on it for something you care about.

## The family

|Part|Crate|What it does|Latest|Docs|
|---|---|---|---|---|
|**The blueprint**|[bevy_blueprint](https://github.com/dark-incorporated/bevy_dark_factory)|What a game loads: a library of pieces and a map, with the grammar learned from your example.|[![crates.io](https://img.shields.io/crates/v/bevy_blueprint.svg)](https://crates.io/crates/bevy_blueprint)|[docs.rs](https://docs.rs/bevy_blueprint) · [book](https://dark-incorporated.github.io/crates/bevy_blueprint.html)|
|**The Dark Factory**|[bevy_dark_factory](https://github.com/dark-incorporated/bevy_dark_factory)|The editor that builds the blueprint: you and the Night Shift place pieces, and the learned grammar fills in more.|git only|[book](https://dark-incorporated.github.io/crates/bevy_blueprint.html)|
|**World**|[bevy_elements](https://github.com/dark-incorporated/bevy_elements)|Sky, weather, wind, clouds, terrain and water, simulated in compute shaders.|[![crates.io](https://img.shields.io/crates/v/bevy_elements.svg)](https://crates.io/crates/bevy_elements)|[docs.rs](https://docs.rs/bevy_elements) · [book](https://dark-incorporated.github.io/crates/bevy_elements.html)|
||[bevy_flora](https://github.com/dark-incorporated/bevy_flora)|Procedural stylized trees and shrubs that grow over time.|[![crates.io](https://img.shields.io/crates/v/bevy_flora.svg)](https://crates.io/crates/bevy_flora)|[docs.rs](https://docs.rs/bevy_flora) · [book](https://dark-incorporated.github.io/crates/bevy_flora.html)|
||[isomesh](https://github.com/dark-incorporated/isomesh)|`isomesh` and `bevy_isomesh`: signed distance fields in, meshes out, with caves and carving.|[![crates.io](https://img.shields.io/crates/v/isomesh.svg)](https://crates.io/crates/isomesh) [![crates.io](https://img.shields.io/crates/v/bevy_isomesh.svg)](https://crates.io/crates/bevy_isomesh)|[docs.rs](https://docs.rs/bevy_isomesh) · [book](https://dark-incorporated.github.io/crates/isomesh.html)|
||[bevy_lights](https://github.com/dark-incorporated/bevy_lights)|Flickering fires and a budgeted pool of real lights over thousands of virtual ones.|[![crates.io](https://img.shields.io/crates/v/bevy_lights.svg)](https://crates.io/crates/bevy_lights)|[docs.rs](https://docs.rs/bevy_lights) · [book](https://dark-incorporated.github.io/crates/bevy_lights.html)|
||[bevy_light_grid](https://github.com/dark-incorporated/bevy_light_grid)|An illuminance grid that creature AI can read and follow.|git only|[book](https://dark-incorporated.github.io/crates/bevy_light_grid.html)|
|**Life**|[bevy_society](https://github.com/dark-incorporated/bevy_society)|Villagers with needs, moods, memories, relationships, rumours and factions living daily lives.|[![crates.io](https://img.shields.io/crates/v/bevy_society.svg)](https://crates.io/crates/bevy_society)|[docs.rs](https://docs.rs/bevy_society) · [book](https://dark-incorporated.github.io/crates/bevy_society.html)|
||[bevy_stigmergy](https://github.com/dark-incorporated/bevy_stigmergy)|Fading marks on a grid that crowds coordinate through, like ant trails.|[![crates.io](https://img.shields.io/crates/v/bevy_stigmergy.svg)](https://crates.io/crates/bevy_stigmergy)|[docs.rs](https://docs.rs/bevy_stigmergy) · [book](https://dark-incorporated.github.io/crates/bevy_stigmergy.html)|
||[bevy_orca](https://github.com/dark-incorporated/bevy_orca)|Walkers that steer around each other without colliding (ORCA avoidance).|[![crates.io](https://img.shields.io/crates/v/bevy_orca.svg)](https://crates.io/crates/bevy_orca)|[docs.rs](https://docs.rs/bevy_orca) · [book](https://dark-incorporated.github.io/crates/bevy_orca.html)|
||[bevy_speech_bubbles](https://github.com/dark-incorporated/bevy_speech_bubbles)|Speech balloons, barks, conversation graphs and a skinnable dialog box.|[![crates.io](https://img.shields.io/crates/v/bevy_speech_bubbles.svg)](https://crates.io/crates/bevy_speech_bubbles)|[docs.rs](https://docs.rs/bevy_speech_bubbles) · [book](https://dark-incorporated.github.io/crates/bevy_speech_bubbles.html)|
|**Interface**|[bevy_gooey](https://github.com/dark-incorporated/bevy_gooey)|Menus, HUD meters, dialogs and tooltips with keyboard and gamepad navigation.|[![crates.io](https://img.shields.io/crates/v/bevy_gooey.svg)](https://crates.io/crates/bevy_gooey)|[docs.rs](https://docs.rs/bevy_gooey) · [book](https://dark-incorporated.github.io/crates/bevy_gooey.html)|
|**Spectacle**|[bevy_carnage](https://github.com/dark-incorporated/bevy_carnage)|Characters that fracture into chunks, with wounds and blood, when they die.|[![crates.io](https://img.shields.io/crates/v/bevy_carnage.svg)](https://crates.io/crates/bevy_carnage)|[docs.rs](https://docs.rs/bevy_carnage) · [book](https://dark-incorporated.github.io/crates/bevy_carnage.html)|
|**Agents and tooling**|[bevy_fairy](https://github.com/dark-incorporated/bevy_fairy)|Lets a coding agent read and drive a running Bevy game over MCP.|[![crates.io](https://img.shields.io/crates/v/bevy_fairy.svg)](https://crates.io/crates/bevy_fairy)|[docs.rs](https://docs.rs/bevy_fairy) · [book](https://dark-incorporated.github.io/crates/bevy_fairy.html)|

## Start here

- [The Dark Inc. book](https://dark-incorporated.github.io/): how the crates fit together, and how to use each one alone or in the Dark Factory.
- [What Dark Inc. is and where it is going](https://github.com/dark-incorporated/.github/blob/main/VISION.md): the goals, the projects, and the names (Dark Inc., Dark Factory, the Night Shift, blueprint).
- [How the crates fit together](https://github.com/dark-incorporated/.github/blob/main/docs/ARCHITECTURE.md): the layers, the dependency edges, and the engine-free crates.
- [How Dark Inc. writes code](https://github.com/dark-incorporated/.github/blob/main/docs/STYLE.md): naming, the machine plate, dependencies, layout, Rust, tests and shipping.
- [How every crate is documented](https://github.com/dark-incorporated/.github/blob/main/DOCUMENTATION.md).
- [Contributing](https://github.com/dark-incorporated/.github/blob/main/CONTRIBUTING.md).

New machine? Set it up with [the workspace guide](https://github.com/dark-incorporated/.github/blob/main/docs/WORKSPACE.md).
