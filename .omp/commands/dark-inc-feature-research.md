---
description: Research one subject for the Dark Factory with the home-still corpus and the open web, then invent new design ideas for the agentic editor. Pulls new sources, reads and cites them, synthesises, ideates through parallel lenses, has the ideas attacked and checked for prior art, and lands a cited research document in dark-incorporated/.github as a pull request. Interactive, one subject per run.
argument-hint: "[--quick|--deep|--exhaustive] <subject text | seed id S-nnn>"
disable-model-invocation: true
---

# Research a subject for the Dark Factory

You research one subject for the Dark Factory (`bevy_dark_factory`, the editor where a person and the Night Shift build a game's world) and invent new design ideas from what you learn.
The ideas are the main deliverable; the reading exists to make them better than what anyone would think of alone.
The owner runs this command and answers four checkpoints; each checkpoint is one `ask` form, and an unanswered form means the draft you showed stands.
The result is one research document in `dark-incorporated/.github/docs/research/`, one home-still synthesis, and one pull request.
It decides nothing: `/dark-inc-feature-backlog` adopts ideas from it later.

Arguments: `$ARGUMENTS`

## 0. Arguments

Run from `~/dark-incorporated/.github`; you read that clone and never edit it (§9 makes the worktree every write goes to).
Parse `$ARGUMENTS`: an optional first token `--quick`, `--deep` or `--exhaustive` (absent means the default tier), then the subject.
A subject matching `^S-\d{3}$` is a seed: read that row of `docs/research/ideas.md` and research its **Idea** text; when the row is missing, stop and say so.
An empty subject: `ask` the owner for one, and offer every seed whose Status is `open` as an option.
Derive `<slug>` from the subject: lower case, words joined by `-`, at most six words.

## 1. Depth tiers

The tier bounds the work. Obey its row:

|Tier|New acquisitions cap|Sources read closely|Source kinds|Citation-graph hops|Ideation lenses|Ideas developed|
|---|---|---|---|---|---|---|
|`--quick`|5|~6|corpus + papers (open access and paywalled)|0|2|top 3|
|default|15|10–20|+ web pages (vendor docs, engine docs)|1|4|top 3–5|
|`--deep`|30|25–40|+ open-source editors' code and docs, conference talks|2|6|top 5–8|
|`--exhaustive`|60 (hard ceiling)|everything relevant|every high-quality kind: papers, books, theses, web and vendor docs, talks (GDC, SIGGRAPH, CHI, UIST, FDG, AIIDE…), open-source code and docs (Godot, Blender, Unreal and Unity public docs, Bevy editor prototypes, Fyrox, Houdini), patents, standards, practitioner forums (Hacker News, Reddit, engine forums)|until saturation|6|top 5–10|

`--exhaustive` stops at saturation: two consecutive search rounds that add no new relevant source, or the 60-acquisition ceiling, whichever comes first.
The document says which of the two ended it.
A forum post or a patent is **reported** confidence at most, never **read**.

## 2. Orient (read-only)

Read, in this order, from `~/dark-incorporated/.github`:

1. `VISION.md` (the names, the goals 1–7);
2. `docs/ARCHITECTURE.md`;
3. `docs/research/README.md`;
4. every `docs/research/*.md` whose title overlaps the subject;
5. `docs/research/ideas.md`.

Then, from `~/dark-incorporated/bevy_dark_factory` (a clone a loop owns: read it, never edit it): `docs/PROJECT.md`, `docs/mcp-tools.md`, `docs/loop/backlog.json` (open items only), `docs/loop/focus.md`, `AGENTS.md`, and `docs/research/README.md`.
`recall` the `syntheses` store with the subject to find earlier runs on it.

Write a brief of at most 40 lines to `local://editor-today.md`: the operation, oplog and undo model; the MCP surface the Night Shift has; the known gaps `PROJECT.md` measures.
Every claim in it names the file it came from.

If an earlier research document covers the subject, this run is a revisit: the new document links the old one, and the old one is never edited.

## 3. Checkpoint A: scope

One `ask` form with:

- the 3–6 research questions you drafted, in an editable textarea;
- the search plan: the queries, the providers, and the source kinds the tier allows;
- the ideation lenses, as checkboxes from the list in §7, with as many preselected as the tier allows;
- the tier, preselected to the one parsed in §0.

The answers replace your drafts.

## 4. Pull sources

home-still's tools are MCP tools (`discover`, `graph`, `acquire`, `status`, `capture`, `read`, `cite`, `documents`, `synthesis_save`); search is the myelin server's `recall` and `investigate`.
Each also runs in bash as `mcp__home_still_<name>` or `mcp__myelin_<name>`, with `--help`.

1. **Corpus first.** `recall` each research question against the stores `academic`, `abstracts`, `web` and `syntheses`, with `k` 8, and note each hit's `store` and `meta.doc_id`.
2. **Discover.** For each query of the plan, `discover` with `source` `providers` (`limit` 20; `year_from` only when the owner set one) and again with `source` `openalex`. A provider search answers `provider_failures`; record them for Method and limits. When every provider fails, retry once; when they fail again, record it and go on with `openalex`, the corpus and the web. When none of those yields a relevant source, stop at Checkpoint B and tell the owner.
3. **Citation graph** (default tier and up). From the 2–3 most relevant DOIs, `graph` in both directions (`citations` and `references`), `sort` `citations`, `limit` 50, for as many hops as the tier allows.
4. **Rank.** Order the candidates by relevance to the research questions, judged by title and abstract. A candidate whose DOI matches a corpus hit of step 1 is already in the corpus: read it, and do not count it against the cap. Cut the rest to the tier's acquisitions cap. Nothing is acquired before Checkpoint B.
5. **Other kinds** (default tier and up). Fetch web pages with your web tools and `capture` each page you rely on, with its whole content, its `content_type` and its title; a summary is not a capture.
   Talks (`--deep` and up): prefer a published transcript or the slides, and `capture` them.
   With neither, fetch the audio with `uvx yt-dlp -x --audio-format m4a -o '/tmp/dark-inc-research/<slug>/%(id)s.%(ext)s' <url>`, transcribe it as the skill `convodump` says, and `capture` the transcript as `text` under the talk's URL.
   A talk that cannot be fetched goes under `Could not obtain` with the error; another site's summary of it is never captured as the talk.
   Open-source code: read the docs and source directly, cite them by repository URL, path and commit, and `capture` the doc pages you rely on.

**Checkpoint B: sources.**
One `ask` form with the ranked candidate table: title, year, venue, kind, why it is relevant, open access or paywalled.
Every candidate up to the cap is preselected; the owner unticks what to skip.

Then acquire what the owner kept:

- `acquire` each DOI.
- The DOIs that fail because no open copy exists go, as one batch, through the skill `ingest-dois-via-anna-scidb`.
- A source that still fails is listed in the document as **unread**, with the reason. Nothing is dropped silently.
- Conversion runs in the background. Start reading the corpus hits at once; before reading a new paper, ask `status` with its `doc_id`. A paper not converted by the end of §5 gets one more `status` check, then is listed as **acquired, not yet read**.

## 5. Read and summarise

For each source, `read` the slices that matter (start from the lines of its `recall` hits) and write a note to `local://sources/<doc_id>.md` with these fields: claim; mechanism; evidence (each number with where it came from); limits; relevance to the Dark Factory.
Pass every quotation through `cite` before it goes in a note. When `cite` refuses a quote, use the passage it names instead, or drop the quote.
Label each source's confidence: **read** (its passage was read and cited), **reported** (a secondary source, a snippet or a forum), or **unread**.

At `--deep` and `--exhaustive`, fan the reading out: one `task` subagent per 4–6 sources, in one batch.
Give each the research questions, its `doc_id`s with their stores, and the note template above; each returns its notes as `local://sources/<doc_id>.md` files and edits nothing else.
Check a sample of their quotes with `cite` yourself before relying on them.

## 6. Synthesise

Write `local://synthesis.md`.
Per research question: what the sources agree on, where they conflict, what is measured and what is argued, and what no source answers.
Then `Implications for the Dark Factory`, read against `local://editor-today.md`.

**Checkpoint C: synthesis.**
One `ask` form with the top-line findings in a textarea, and a free-text field for corrections.
Apply the owner's corrections to `local://synthesis.md` before §7.

## 7. Innovate

This is the main deliverable.

**Lenses.** The tier says how many; the owner chose which at Checkpoint A:

1. **Night Shift interface**: the shape of the tools, the feedback an agent gets, guardrails, what an agent can perceive.
2. **Human authoring**: what a person does with their hands and eyes in the editor.
3. **Procedural and grammar-driven generation** from the blueprint.
4. **Provenance, undo, the oplog**, and collaboration between a person and an agent.
5. **Verification and seeing**: stills, the decision model, tests of a world.
6. **Live reload, performance and scale.**

**Divergent pass.** One `task` subagent per chosen lens, all in one batch.
Each gets `local://synthesis.md`, `local://editor-today.md`, the seed's Idea text if there is one, and the goals of `VISION.md`.
Each edits no files and returns 2–4 ideas, each in exactly this schema:

- `title`;
- `problem`: who hurts, when, and the evidence;
- `mechanism`: the mechanism from a source, adapted, with its `doc_id` or URL;
- `sketch`: in Dark Factory terms, which operations, MCP tools, oplog entries or blueprint data change, what a person sees, and what an agent calls;
- `why new`: the novelty claimed;
- `test`: one falsifiable acceptance check.

**Convergent pass.** Two `task` subagents in one batch:

- a **critic**, who attacks each idea on its feasibility in the current codebase, its conflict with any of the goals 1–7, its hidden cost, and whether it is a feature or a gimmick;
- a **prior-art** searcher, who runs a web search per idea (does Unity, Unreal, Godot, Houdini, Blender, Roblox, Dreams, Fortnite UEFN or an MCP server already do it?), cites URLs, and `capture`s each page relied on.

Merge duplicates.
Drop an idea the critic shows is infeasible, or the prior-art search shows is already standard, and keep one line for each drop saying why.
Score each survivor from 1 to 5 on:

- **Evidence**: how directly the sources support it;
- **Novelty**: after the prior-art search;
- **Vision fit**: against the goals 1–7;
- **Leverage**: how much better a person and the Night Shift build worlds with it;
- **Cost**: 5 is the cheapest.

Rank by the sum; Evidence breaks a tie.

**Checkpoint D: ideas.**
One `ask` form with a table of every surviving idea: title, one-line sketch, the five scores.
Checkboxes preselect the tier's top N as **recommended**; a textarea takes the owner's annotations per idea.
The owner's selection and annotations go into the document verbatim.

## 8. Contradiction report (read-only)

For each recommended idea and each major finding, search the family's clones for guidance it contradicts or makes stale.
Search with `rg` over `~/dark-incorporated/*/`: the docs, `AGENTS.md`, `CLAUDE.md`, `README.md`, and comments in `*.rs`.
Include the retired names (Cauldron, grimoire, Coven, Familiar) in any text the document relies on.
Record each hit as `repo/path:line — what it says — what this research says`.
Nothing outside the research worktree is edited: fixing guidance is `/dark-inc-feature-backlog`'s job.

## 9. Write the document

Make the worktree:

```sh
git -C ~/dark-incorporated/.github fetch origin
git -C ~/dark-incorporated/.github worktree add -b research/<YYYY-MM-DD>-<slug> /tmp/dark-incorporated/.github-research-<slug> origin/main
```

Write `docs/research/<YYYY-MM-DD>-<slug>.md` in it, with exactly these sections, in this order:

1. The title, then `Written <date> at .github commit <sha>. **Status: findings and proposals, not a decision.** Adopted through /dark-inc-feature-backlog.`, then the tier, the seed id if there is one, and the home-still synthesis `doc_id` (filled in by §10).
2. `## The question`: the question in one sentence, then the research questions.
3. `## Sources`: a table of source, kind, where from (`doc_id`, DOI or URL), confidence (read, reported or unread) and one line of relevance. Then the lists `Acquired, not yet read` and `Could not obtain`, each item with its reason.
4. `## What the sources say`: per research question, with cited quotes, every claim labelled measured or reasoned.
5. `## The Dark Factory today`: from `local://editor-today.md`, each claim with its file.
6. `## Ideas`: one `### I<n>. <title>` per surviving idea, in rank order, with the §7 schema fields, the prior art with links, the critic's verdict, the five scores, and the owner's annotation. A recommended idea is marked `**Recommended (owner, <date>)**`.
7. `## Dropped ideas`: one line each, with the reason.
8. `## Guidance this contradicts`: the §8 list, or `None found` followed by the searches that were run.
9. `## Alternatives and what would decide them`: for each recommended idea, the main alternative design and the evidence that would settle the choice.
10. `## Method and limits`: every query and provider, every tool failure, the stop reason (the cap or saturation), and what was not read.

Use only the current vocabulary (Dark Factory, Night Shift, blueprint, work order); a retired name appears only inside a quote.
Write one sentence per line, with no hard wraps.

Add one line under `## Documents` in `docs/research/README.md`:

```markdown
- [`<file>`](<file>): <question>. **Findings and proposals**; <n> ideas, <k> recommended.
```

If the subject was a seed, set that row's **Status** in `docs/research/ideas.md` to `researched` and put a link to the document under **Research**.
Nothing else in that file changes.

## 10. Save to home-still

`synthesis_save` with:

- `title`: the question;
- `body`: section 4 of the document and the recommended ideas of section 6;
- `citations`: every `{store, doc_id, quote}` used in section 4, each already passed by `cite`;
- `tags`: `dark-inc`, `feature-research`, `<slug>`.

A refusal names the bad citation: fix that quote through `cite` and retry once.
Refused again: stop and report; the document is never committed with a broken citation.
Put the returned `doc_id` in the document's header.

## 11. Deliver

In the worktree:

```sh
git add docs/research/<file> docs/research/README.md   # and docs/research/ideas.md for a seed
git commit -m "research(<slug>): <the question, at most 60 characters>" -m "<tier; sources read; ideas recommended>"
git push -u origin research/<YYYY-MM-DD>-<slug>
gh pr create -R dark-incorporated/.github --title "Research: <the question>" --body "<summary; the recommended ideas; Next: /dark-inc-feature-backlog docs/research/<file>>"
```

Report to the owner: the pull request's URL, the document's path, the synthesis `doc_id`, the counts (acquired, read, unread), and the recommended ideas.
The worktree stays until the pull request merges.

## Rules

- Never edit a `~/dark-incorporated/<repo>` clone: every write goes to the research worktree, `local://`, or home-still.
- Never add a row to `docs/research/ideas.md` or edit its **Idea** column.
- Never present a quote that `cite` refused.
- Never call an idea new without the prior-art search behind it.
- Never edit an older research document.
- One sentence per line in markdown.
- A failed tool call is retried once, then recorded under `## Method and limits`.
