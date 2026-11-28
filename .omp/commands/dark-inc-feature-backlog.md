---
description: Adopt the recommended ideas of one /dark-inc-feature-research document. Turns them into enhancement issues in the family repos that own the work, records the decision in the research document and the org's reference documents, and removes every piece of stale or contradictory guidance it creates across the family (docs, AGENTS.md, code comments) through one pull request per affected repo. Interactive; it drafts everything, the owner confirms, then it files.
argument-hint: "<docs/research/<file>.md | its date-slug stem>"
disable-model-invocation: true
---

# Adopt a research document's ideas

You turn the ideas the owner adopts from one `/dark-inc-feature-research` document into backlog issues in the repositories that own the work, and you leave the family's guidance saying one thing about them.
Guidance means the org's reference documents, every repository's `README.md`, `docs/`, `AGENTS.md`, `CLAUDE.md` and `.omp/commands/`, and the doc comments and code comments that state a design.
The owner runs this command and answers two checkpoints, each one `ask` form; nothing is filed, pushed or commented before the second is answered.

Document asked for: `$ARGUMENTS`

## 0. Arguments

Run from `~/dark-incorporated/.github`; read that clone, never edit it.
`git -C ~/dark-incorporated/.github fetch origin` first.
`$ARGUMENTS` is a path under `docs/research/`, or its stem `<YYYY-MM-DD>-<slug>`; read the document from `origin/main` (`git show origin/main:docs/research/<file>`).
Stop and say so when the file is missing, when it has no `## Ideas` section, or when no idea in it is marked **Recommended**.
When the document's pull request is still open (`gh pr list -R dark-incorporated/.github --head research/<stem> --state open` prints a row), read it from `origin/research/<stem>` instead, base the org worktree of §7 on that branch, and say so in the report.

## 1. Read

- the research document, whole;
- `docs/research/ideas.md`;
- `VISION.md` (the names; the goals 1–7; `## How this document is kept true`);
- `docs/ARCHITECTURE.md` (the layers, and what may depend on what);
- `docs/STYLE.md`, `docs/README.md`, `CONTRIBUTING.md`;
- `docs/EDITOR-DESIGN.md`, if it exists;
- for each repository an idea could land in: its open issues (`gh issue list -R dark-incorporated/<repo> --state open --limit 200`) and its `AGENTS.md`.

## 2. Checkpoint 1: which ideas

One `ask` form listing every idea of the document, with the **Recommended** ones preselected; the owner adds or removes.
A recommended idea the owner leaves out is recorded as `not adopted (owner, <date>)`, with the owner's reason when one is given.

## 3. Decompose into issues

Each adopted idea becomes 1–6 issues, each one deliverable that a loop pass can ship and prove alone.

**The owning repository**, by `docs/ARCHITECTURE.md`:

- an editor behaviour, an operation, an MCP tool, or a change to the blueprint data (`blueprint_model`, `bevy_blueprint`, `dark_factory_mcp` all live in that workspace) → `bevy_dark_factory`, with the crate named in `## Proposal`;
- a capability that works without the editor → the crate that owns it, by goal 1 of `VISION.md`;
- a capability no crate owns yet → `bevy_dark_factory`, with the open question of where it should live under `## Notes` for the owner.

Show the reason for each routing in the draft.

**The body** has exactly these headings:

- `## Why`: the problem; a link to the idea, `https://github.com/dark-incorporated/.github/blob/main/docs/research/<file>#i<n>-<title-anchor>`; the key DOIs.
- `## Proposal`: the operations, MCP tools, data and interface it touches.
- `## Acceptance`: a test that fails today and passes after, as `CONTRIBUTING.md` asks.
- `## Depends on`: the other issues of this batch, by title until they have numbers.
- `## Notes`: the prior art, and the critic's caveats.

**The title** is imperative, at most 70 characters, with no ticket prefix.
**The labels** are `enhancement` and `research`.

**Dedupe** before drafting a new issue: `gh issue list -R dark-incorporated/<repo> --state all --search "<3–5 key words> in:title,body"`, and the open issues read in §1.
An equivalent open issue gets a comment linking the research instead of a new issue.
An equivalent closed issue is named in the draft, and the owner decides.

## 4. Draft the guidance changes

Write every draft under `local://adopt-<slug>/`; nothing is edited yet.

- **The research document**: append `## Decision (<date>)`, listing the adopted ideas with their issues and the not-adopted ones with the owner's reason when given. Never edit its earlier sections.
- **`docs/EDITOR-DESIGN.md`**: the adopted design principles of the Dark Factory, one `## <principle>` section each, stated as rules in the present tense, each linking its research document and its issues. When this file does not exist yet, create it with a one-line purpose at the top, and in the same change add its row to the table in `docs/README.md` (`How the Dark Factory is designed, and why each rule holds` → [`EDITOR-DESIGN.md`](EDITOR-DESIGN.md)) and a bullet under `## Start here` in `profile/README.md`, in the form the other bullets have.
- **`VISION.md`, `docs/ARCHITECTURE.md`, `docs/STYLE.md`**: edit only where an adopted idea changes a goal, a layer or dependency edge, or a code rule. A changed goal says why and links the research, as `VISION.md` requires; the commit body cites the research document.
- **An affected crate's `README.md`, `docs/` or `AGENTS.md`**: edit only when the adopted idea changes guidance it states.

## 5. Sweep for stale and contradictory guidance

For every decision of §4, search every family repository's `origin/main` for text that now contradicts it:

```sh
git -C ~/dark-incorporated/<repo> fetch origin
git -C ~/dark-incorporated/<repo> grep -n -i -E '<terms>' origin/main -- '*.md' '*.rs' '*.toml' '*.ron' '*.yaml'
```

The clones are read-only: `fetch` and `grep` only.
Look in docs, `AGENTS.md`, `CLAUDE.md`, READMEs, doc comments and code comments, and `.omp/commands/*.md`, and start from the research document's own `## Guidance this contradicts` list.
Include the retired names (Cauldron, grimoire, Coven, Familiar) where they sit in text the decision touches.
Each hit gets proposed replacement text, saved as `local://adopt-<slug>/<repo>.diff`.

Out of the sweep:

- a change of behaviour: that is an issue of §3, not a doc fix;
- tests, golden files, fixtures and the harness;
- older research documents: they are records, never rewritten;
- `docs/loop/focus.md` in any repository: it is the owner's; list each hit in the report instead.

## 6. Checkpoint 2: confirm the whole draft

One `ask` form showing:

- the issues table: repository, title, labels, depends on, and new or comment on an existing issue;
- the guidance changes per file: a short summary and its `local://adopt-<slug>/<repo>.diff` path;
- the stale-guidance fixes per repository.

A checkbox per issue and per repository pull request, all preselected, and a textarea for edits.
Nothing is filed, commented, committed or pushed before this answer; a cancelled form ends the run with nothing done.

## 7. Execute

In this order:

1. **The label**, in each target repository:
   `gh label create research -R dark-incorporated/<repo> --color 5319e7 --description "From a /dark-inc-feature-research document" --force`.
   When the label cannot be created there, file that repository's issues with `enhancement` alone and say so in the report.
2. **The issues**, in dependency order: `gh issue create -R dark-incorporated/<repo> --label enhancement --label research --title "<title>" --body-file <file>`.
   Then rewrite each `## Depends on` from titles to `#<n>` (or `dark-incorporated/<repo>#<n>` across repositories) with `gh issue edit --body-file`.
   Post the comments on the equivalent existing issues.
3. **The org pull request.**
   `git -C ~/dark-incorporated/.github worktree add -b adopt/<YYYY-MM-DD>-<slug> /tmp/dark-incorporated/.github-adopt-<slug> origin/main`, or on `origin/research/<stem>` when §0 found the research pull request still open.
   Apply the org changes of §4, with the real issue numbers, and the org repository's fixes from §5.
   When the document came from a seed, set that row's **Status** in `docs/research/ideas.md` to `adopted` (or `dropped` when no idea was adopted) and put the issue links under **Issues**; nothing else in that file changes.
   Commit `adopt(<slug>): <n> ideas → <m> issues`, push, and `gh pr create -R dark-incorporated/.github`.
4. **One pull request per other affected repository.**
   `git -C ~/dark-incorporated/<repo> fetch origin && git -C ~/dark-incorporated/<repo> worktree add -b adopt/<slug> /tmp/dark-incorporated/<repo>-adopt-<slug> origin/main`.
   Docs and comments only.
   When any `.rs` file changed, run `CARGO_TARGET_DIR=$HOME/.cargo-target-shared/global cargo check --workspace` and `cargo fmt --check` in that worktree; both must pass.
   Commit `docs: align with <research document> decisions`, push, and `gh pr create` with a body linking the org pull request and the issues.
5. **Cross-link**: edit the org pull request's body to list every repository's pull request.

## 8. Report

- the issues filed (`<repo>#<n>`, title) and the comments posted;
- the pull requests' URLs;
- the guidance files changed;
- the stale hits fixed, and those deferred with the reason;
- what the owner must decide: closed-issue duplicates, `focus.md` hits, routings left open.

The worktrees stay until their pull requests merge.

## Rules

- Never edit a `~/dark-incorporated/<repo>` clone, and never push to `main`.
- Never use the `owner` label: it is the owner's steer for the loops.
- Never edit tests, golden files, fixtures or harness files.
- Never rewrite an older research document's findings; a decision is appended.
- Never add a row to `docs/research/ideas.md` or edit its **Idea** column.
- One sentence per line in markdown.
- A failed `gh` call is retried once, then reported; the steps after it go on only when they do not depend on it.
