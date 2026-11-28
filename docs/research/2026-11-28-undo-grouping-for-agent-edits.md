# Undo grouping for agent edits: how a person and the Night Shift should share one history

Written 2026-11-28 at .github commit af27dad. **Status: findings and proposals, not a decision.** Adopted through `/dark-inc-feature-backlog`.
Tier: `--exhaustive` (cap 60). Synthesis in home-still: store `syntheses`, `2621d961-when-the-night-shift-makes-a-multi-step-change-to-a-blueprin`.
Revisits [`2026-11-02-game-editor-best-practices.md`](2026-11-02-game-editor-best-practices.md), which raised undo grouping for agent turns as an open question; that file is not rewritten.

## The question

When the Night Shift makes a multi-step change to a blueprint that a person is also editing, what should one undo take back, whose edits may it reach, and what must the person see before and after it?

Four research questions:

1. **RQ1, the unit's edge.** Where should an undo unit end: at a time gap, at the actor's intent, at a declared transaction, or at a change of actor?
2. **RQ2, interleaved actors.** How should selective undo behave when another actor's edits sit between the change and now, and when must it refuse?
3. **RQ3, trust, inspect, revert.** What does a person need to trust, inspect and revert an agent's multi-step change?
4. **RQ4, too coarse or too fine.** What do user studies say about grouping that is too coarse or too fine?

Lenses: the Night Shift interface; human authoring; procedural and grammar generation; provenance, undo and the oplog; verification and seeing; live reload, performance and scale; and, added by the owner, UI and UX for agentic development.

## Sources

|Source|Kind|Where from|Confidence|Relevance|
|---|---|---|---|---|
|Abowd & Dix 1992|paper|`10.1016_0953-5438(92)90021-7` [doi](https://doi.org/10.1016/0953-5438(92)90021-7)|read|RQ1, RQ2, RQ3: Local undo equals global undo only when intervening actions commute; otherwise ask the user.|
|ACRFence: Zheng et al. 2026|paper|`10.48550_arxiv.2603.20625` [doi](https://doi.org/10.48550/arXiv.2603.20625)|read|RQ2: All 10 checkpoint-restore trials produced duplicate commits against 0 of 10 without checkpoints, so restore misses external effects.|
|AgentRewind: Zhuang et al. 2026|paper|`10.48550_arxiv.2608.14380` [doi](https://doi.org/10.48550/arXiv.2608.14380)|read|RQ1, RQ2, RQ3: Rewinding to an LLM-decision checkpoint scored 87.8% against 62.2% for continuing, but 43.9% without environment rewind.|
|Akers et al. 2009|paper|`10.1145_1518701.1518804` [doi](https://doi.org/10.1145/1518701.1518804)|read|RQ3: Logged undo and erase events flagged 23 of 25 severe SketchUp problems (n=35): undo is a cheap usability signal.|
|Akers et al. 2012|paper|`10.1145_2240156.2240164` [doi](https://doi.org/10.1145/2240156.2240164)|read|RQ1, RQ3, RQ4: Users also undo 'just to make sure' nothing changed, so not every undo is an error.|
|Amershi et al. 2019|paper|`10.1145_3290605.3300233` [doi](https://doi.org/10.1145/3290605.3300233)|read|RQ3: Guidelines G9, G10, G11 and G16 cover recovery and consequences; 49 practitioners rated 20 products, none an agentic editor.|
|Aquamarine: Myers et al. 2015|paper|`10.1145_2702123.2702543` [doi](https://doi.org/10.1145/2702123.2702543)|read|RQ1, RQ2, RQ3, RQ4: Main request was grouping actions; exact pixel-level conflict detection was abandoned for 'too many false positives'.|
|Archer et al. 1984|paper|`10.1145_357233.357234` [doi](https://doi.org/10.1145/357233.357234)|read|RQ2: Warns that undoing an interior command gives a state hard to anticipate; models command size and reach explicitly.|
|Atomix: Mohammadi et al. 2026|paper|`10.48550_arxiv.2602.14849` [doi](https://doi.org/10.48550/arXiv.2602.14849)|read|RQ1, RQ2: Unit is the smallest agent intent settling together; leaked 0 of 500 irreversible sends, Saga compensation 400.|
|Azurite: Yoon & Myers 2015|paper|`10.1109_icse.2015.43` [doi](https://doi.org/10.1109/icse.2015.43)|read|RQ1, RQ2, RQ3, RQ4: Three conflict outcomes halved backtracking time, 386.3 s against 768.8 s (n=12, p<0.01).|
|Berlage 1994|paper|`10.1145_196699.196721` [doi](https://doi.org/10.1145/196699.196721)|read|RQ1, RQ2: Selective undo whose result depends only on the command and current state; an inapplicable undo is not offered.|
|Brown & Patterson 2002|paper|`10.1145_1133373.1133387` [doi](https://doi.org/10.1145/1133373.1133387)|read|RQ2: Rewind, repair, replay: restore an earlier state, drop the bad action, re-run later users' logged intents with preconditions checked.|
|Cass et al. 2006|paper|`10.1145_1182475.1182478` [doi](https://doi.org/10.1145/1182475.1182478)|read|RQ2: Asked what undoing step 1 should do, 18 of 28 people chose cascading selective undo (7 script, 1 linear).|
|Causality: Nancel & Cockburn 2014|paper|`10.1145_2556288.2556990` [doi](https://doi.org/10.1145/2556288.2556990)|read|RQ1, RQ2: Every command records user, date, targets and results, making conflicts after a history edit computable and user-resolvable.|
|Chen & Sun 2001|paper|`10.1145_500286.500316` [doi](https://doi.org/10.1145/500286.500316)|read|RQ2: Defines correct selective undo (Definitions 10-11) via a mask policy: an undone operation stays in history, marked undone.|
|Chen et al. 2016|paper|`10.1145_2856400.2856417` [doi](https://doi.org/10.1145/2856400.2856417)|read|RQ1, RQ3, RQ4: History groups same-command runs on one region or under 500 ms; navigation time fell (n=6, p=0.0014).|
|Cheng et al. 2014|paper|`10.7315_jcde.2014.011` [doi](https://doi.org/10.7315/jcde.2014.011)|read|RQ2: Cascade policy: undoing a feature also undoes later features that depend on it, via a dependency hierarchy.|
|Cheng et al. 2023|paper|`10.1145_3610220` [doi](https://doi.org/10.1145/3610220)|read|RQ3, RQ4: 221 of 719 coded CAD forum threads cite branching shortcomings, chiefly whole-file granularity and poor history visualisation.|
|Chimera: Kurlander & Feiner 1988|paper|`10.1109_wvl.1988.18020` [doi](https://doi.org/10.1109/wvl.1988.18020)|read|RQ1, RQ3: Panels group commands by pair rules and user-set granularity, so a person can undo to any shown state.|
|Chou et al. 2025|paper|`10.1145_3797105` [doi](https://doi.org/10.1145/3797105)|read|RQ1, RQ3, RQ4: Coders seek undo and version control as guardrails because agent edits reach unrelated code (20 videos).|
|Chronicle: Grossman et al. 2010|paper|`10.1145_1866029.1866054` [doi](https://doi.org/10.1145/1866029.1866054)|read|RQ1, RQ3, RQ4: At most 7 items per level; 8 participants finished all five navigation tasks in under 2 minutes.|
|Cordon: Liu et al. 2026|paper|`10.48550_arxiv.2606.17573` [doi](https://doi.org/10.48550/arXiv.2606.17573)|read|RQ1, RQ2, RQ3, RQ4: Unit is the delegated task; rollback left 0 residual deltas against 73 for git restore.|
|Decriteau et al. 2016|paper|`10.1080_16864360.2016.1168217` [doi](https://doi.org/10.1080/16864360.2016.1168217)|wrong file|Not used: home-still stored a different paper under this DOI.|
|DistEdit: Prakash & Knister 1994|paper|`10.1145_198425.198427` [doi](https://doi.org/10.1145/198425.198427)|read|RQ2, RQ4: A conflict rule too strict was 'too restrictive in practice' and frustrated users; DistEdit later shipped partial undo.|
|Dwell-and-spring: Appert et al. 2012|paper|`10.1145_2207676.2208339` [doi](https://doi.org/10.1145/2207676.2208339)|read|RQ4: More than half of 12 participants wanted the spring widget to trigger several undos in one step.|
|Edwards et al. 2000|paper|`10.1145_354401.354409` [doi](https://doi.org/10.1145/354401.354409)|read|RQ1, RQ2, RQ3: Nested transactions with explicit open/close entries; history may be entered or left only at transaction boundaries.|
|EvoGraph: Exarhakos et al. 2026|paper|`10.48550_arxiv.2604.18883` [doi](https://doi.org/10.48550/arXiv.2604.18883)|read|RQ1, RQ3, RQ4: Commit-sized units were too coarse for AI edits; prompt-sized branching checkpoints lowered frustration (n=20).|
|Heer et al. 2008|paper|`10.1109_tvcg.2008.137` [doi](https://doi.org/10.1109/tvcg.2008.137)|read|RQ1, RQ3, RQ4: Chunking and undo-as-delete removed or chunked 61.7% of 17,401 Tableau history items, yet Undo steps per action.|
|Horvitz 1999|paper|`10.1145_302979.303030` [doi](https://doi.org/10.1145/302979.303030)|read|RQ3: Act only when expected value beats inaction, keep the cost of poor guesses low, and allow efficient direct termination.|
|LAVE: Wang et al. 2024|paper|`10.1145_3640543.3645143` [doi](https://doi.org/10.1145/3640543.3645143)|read|RQ3, RQ4: Plan first, then approve each action: 8 users kept control; sequential approval is a stated cost.|
|Liu et al. 2020|paper|`10.1145_3313831.3376152` [doi](https://doi.org/10.1145/3313831.3376152)|read|RQ1, RQ3, RQ4: Kappa 0.77 for low-level chunk starts but 'little agreement' on high-level chunks (16 sessions, 13 people).|
|Lv et al. 2019|paper|`10.1016_j.future.2019.05.021` [doi](https://doi.org/10.1016/j.future.2019.05.021)|read|RQ2: Gives a concrete dependency rule for when a CAD feature undo can be applied, with case studies on SolidWorks.|
|Magentic-UI: Mozannar et al. 2025|paper|`10.48550_arxiv.2507.22358` [doi](https://doi.org/10.48550/arXiv.2507.22358)|read|RQ1, RQ3, RQ4: Participants (P1-P12) found approval requests excessive and long task histories overwhelming; guards target irreversible actions.|
|MeshFlow: Denning et al. 2011|paper|`10.1145_1964921.1964961` [doi](https://doi.org/10.1145/1964921.1964961)|read|RQ1, RQ3, RQ4: Eleven hand-built levels cut one model's 8,510 operations to 108; all 8 students preferred the clustered view.|
|Myers & Kosbie 1996|paper|`10.1145_238386.238526` [doi](https://doi.org/10.1145/238386.238526)|read|RQ1: Only the top-level command is listed and undone, children going with it; a dialog can expand it per object.|
|Prakash & Knister 1992|paper|`10.1145_143457.143527` [doi](https://doi.org/10.1145/143457.143527)|read|RQ1, RQ2: Refuse policy: an operation cannot be undone if a later operation conflicts, unless that is undone first.|
|RaivenTracks: Hugie et al. 2026|paper|`10.48550_arxiv.2608.14869` [doi](https://doi.org/10.48550/arXiv.2608.14869)|read|RQ1, RQ3, RQ4: Debounces settings at 300 ms; three participants kept undo apart from tree restore (n=3, qualitative).|
|Rasch et al. 2024|paper|`10.1145_3613904.3642864` [doi](https://doi.org/10.1145/3613904.3642864)|read|RQ1, RQ2, RQ3, RQ4: One-object selective undo raised load (TLX 42.0 against 34.4, 34.6); WorldUndo scored IOS 4.48 (n=32).|
|Ressel & Gunzenhäuser 1999|paper|`10.1145_320297.320312` [doi](https://doi.org/10.1145/320297.320312)|read|RQ1: Applying an inverse to the current state fails once others edited; mirror and fold operators repair local group undo.|
|Ressel et al. 1996|paper|`10.1145_240080.240305` [doi](https://doi.org/10.1145/240080.240305)|read|RQ2: adOPTed treats an undo as a concurrent operation, giving local group undo, with a Shadow rule holding blocked undos.|
|Revisable by Design: Zhai et al. 2026|paper|`10.48550_arxiv.2604.23283` [doi](https://doi.org/10.48550/arXiv.2604.23283)|read|RQ1, RQ3: Rolls back to just before the earliest conflicting action, wasting less work than restart (1,008 runs, no humans).|
|SagaLLM: Chang & Geng 2025|paper|`10.14778_3750601.3750611` [doi](https://doi.org/10.14778/3750601.3750611)|read|RQ1: Unit is one operation plus its compensating operation inside a plan, with validation and context management across agents.|
|Sagas: Garcia-Molina & Salem 1987|paper|`10.1145_38713.38742` [doi](https://doi.org/10.1145/38713.38742)|read|RQ1, RQ2: Steps with compensating transactions; compensation does not restore old state and 'no effort is made to notify' readers.|
|Seifried et al. 2012|paper|`10.1145_2207676.2208690` [doi](https://doi.org/10.1145/2207676.2208690)|read|RQ1, RQ2, RQ4: Regional undo matched expectations 86% (n=23); 23 of 26 clustering errors were too-large clusters (n=18).|
|Semantic Commit: Vaithilingam et al. 2025|paper|`10.1145_3746059.3747778` [doi](https://doi.org/10.1145/3746059.3747778)|read|RQ3, RQ4: ChatGPT Canvas rewrites forced version-history restores in 8 instances across 6 of 12 participants; per-item revert preferred.|
|Spenke 1993|paper|`10.1145_169059.169399` [doi](https://doi.org/10.1145/169059.169399)|read|Background: A tree of command objects gives linear undo, selective undo, replay and multi-user cooperation from one mechanism; demo only.|
|Stewen & Kleppmann 2024|paper|`10.1145_3642976.3653029` [doi](https://doi.org/10.1145/3642976.3653029)|read|RQ2: Five of six tested collaboration apps give local undo; Miro blocks undo when another user's operation arrives.|
|Sun 2000|paper|`10.1145_358916.358990` [doi](https://doi.org/10.1145/358916.358990)|read|RQ2: Mask policy: undo as a concurrent inverse always succeeds; an overwritten operation's undo has no visible effect.|
|Sun 2002|paper|`10.1145_586081.586085` [doi](https://doi.org/10.1145/586081.586085)|read|RQ1, RQ2: Compound operations share one id and undo all primitives at once; invisible undos are reported.|
|Tanagra: Smith et al. 2010|paper|`10.1145_1822348.1822376` [doi](https://doi.org/10.1145/1822348.1822376)|read|RQ3: Pins designer-placed geometry the generator never moves and reports 'no solution' rather than override a person; never user-tested.|
|Yoon & Myers 2014|paper|`10.1109_vlhcc.2014.6883030` [doi](https://doi.org/10.1109/vlhcc.2014.6883030)|read|RQ1, RQ3, RQ4: 15,095 backtracks in 1,460 hours (21 programmers): 9.5% selective, 63% of those redone by hand.|
|Yu et al. 2019|paper|`10.4230_lipics.opodis.2019.14` [doi](https://doi.org/10.4230/LIPIcs.OPODIS.2019.14)|read|RQ2: Cascade policy for CRDTs: undo invalidates dependent operations, but composite operations are not handled.|
|aider Git integration docs|docs|`2fa78aa7f0249c97fb15813bb8f7c493` [link](https://aider.chat/docs/git.html)|read|RQ1, RQ2, RQ3: Commits the person's dirty files first, then one commit per reply, keeping person and agent histories apart.|
|Ask HN: Is Cursor deleting working code?|forum|`298285d283098462a7077a2b7030f259` [link](https://news.ycombinator.com/item?id=43298275)|reported|RQ2, RQ3, RQ4: Practitioners commit supervised good states in Git because Cursor reverts lost working code (early-2025, two commenters).|
|Blender Manual: Undo and Redo|docs|`8c3efbef9281f5a269c7c2f9efc4f588` [link](https://docs.blender.org/manual/en/latest/interface/undo_redo.html)|read|Background: Undo History is a linear list you can jump along, truncated by any new change.|
|Claude Code checkpointing docs|docs|`e1b1cfb053fa480b2cb6f06108f8a004` [link](https://code.claude.com/docs/en/checkpointing.md)|read|RQ1, RQ2, RQ3: One checkpoint per person prompt (last 100); outside edits are 'normally not captured'.|
|Claude Code issue #101188|issue|`e1ca01afd6c3cec35566b25de84cfce9` [link](https://github.com/anthropics/claude-code/issues/101188)|reported|RQ1, RQ2, RQ3, RQ4: A rewind that reported failure still overwrote about 20 hours of edits; criteria: atomic, listed, undoable.|
|Cline checkpoints docs|docs|`e32bfecc4644c85a1bba96025f5e74b6` [link](https://docs.cline.bot/core-workflows/checkpoints.md)|read|RQ1, RQ3: Checkpoint after every tool use in a shadow Git repository, with diff before restore; argues rollback replaces approval.|
|Codex review pane docs|docs|`0ea6d87cd4d4388433682ef2a8160b38` [link](https://learn.chatgpt.com/docs/code-review?surface=app)|read|RQ1, RQ3: Diff, file and hunk review plus a 'Last turn' scope over mixed history; no per-hunk provenance elsewhere.|
|Cursor Agent checkpoints docs|docs|`120a3c4465d068a43113a4c5ee4ee233` [link](https://cursor.com/docs/agent/overview)|read|RQ1, RQ3: Agent-judged 'significant' change sets checkpoints, restoring files only; the person cannot predict where one falls.|
|Cursor forum: Problems with revert|forum|`99f09380aa98e01fdeaf4dafb043bb8d` [link](https://forum.cursor.com/t/problems-with-revert/145437)|reported|RQ1, RQ2, RQ3, RQ4: Revert took the user's manual edits back to the checkpoint state; checkpoints track only agent changes.|
|Excalidraw PR #7348 multiplayer undo|issue|`073126be618fda18ff6615e98081db97` [link](https://github.com/excalidraw/excalidraw/pull/7348)|read|RQ2: Local-only invertible deltas; history skips entries with no visible effect and refreshes the opposite entry with conflicting values.|
|Figma: How Figma's multiplayer technology works|vendor blog|`cd78ede99e32a0df25d3bff89cb9b723` [link](https://www.figma.com/blog/how-figmas-multiplayer-technology-works/)|read|RQ2: Figma's per-user scope is inferred from a deleted-object detail; redo must not overwrite later edits.|
|Godot EditorUndoRedoManager class docs|docs|`ef30172c8394ad92f5b654119ae2db0f` [link](https://docs.godotengine.org/en/stable/classes/class_editorundoredomanager.html)|read|Background: One history per edited scene plus a global one, routed by the first operation's object.|
|Godot UndoRedo class docs|docs|`0e1deab8a3c17d57fac0c158fa61d190` [link](https://docs.godotengine.org/en/stable/classes/class_undoredo.html)|read|RQ1: Named actions merge by mode: MERGE_DISABLE, MERGE_ENDS (keep first undo, last do) or MERGE_ALL.|
|Houdini hou.undos docs|docs|`2c21ba4fb9c1db9d9ef30572b306805f` [link](https://www.sidefx.com/docs/houdini/hom/hou/undos.html)|read|RQ1: `with hou.undos.group(label)` is a caller-owned scope; the nearest enclosing group wins.|
|Implement Undo and Redo in Unreal Engine (Lewicki)|vendor blog|`1280409f1d868e2e7e1af8596b4d2e8d` [link](https://unreal.robertlewicki.games/p/implement-undo-and-redo-in-unreal-engine)|reported|RQ1: Documents two meanings of 'cancel', dropping the record versus reverting changes; an agent-turn API must say which.|
|Ink & Switch Patchwork edit groups|vendor blog|`6f505acab14b72a0ccd62da621b1b123` [link](https://www.inkandswitch.com/patchwork/notebook/2024-version-control/05/)|read|RQ1, RQ3: Reviewers group edits after the fact with a rationale and revert a group regardless of time order.|
|Junie issue JUNIE-2018|issue|`62535f2859727ddb0894fccbba40358e` [link](https://youtrack.jetbrains.com/issue/JUNIE-2018)|reported|RQ1, RQ2, RQ3, RQ4: Rollback also reverts later manual changes, and three unlabelled buttons hid its extent.|
|Junie rollback docs|docs|`0bfb723fa3859cabe2846ece06ccf5da` [link](https://www.jetbrains.com/help/ai-assistant/junie-agent.html)|read|RQ1, RQ3: Rollback is per file or all files, the coarsest useful revert unit.|
|Liveblocks multiplayer undo/redo blog|vendor blog|`8a0488d70a3250e331a8a055ee41c279` [link](https://liveblocks.io/blog/how-to-build-undo-redo-in-a-multiplayer-environment)|read|RQ1, RQ2: Undo is client-specific; undoing a conflicting delete is a silent no-op, the quiet end of the refusal spectrum.|
|Loro issue #1229|issue|`c8ee0c0219ed9d82abdcd2c2c5743cd2` [link](https://github.com/loro-dev/loro/issues/1229)|reported|RQ1, RQ2: A local undo removed another peer's later blue mark: local-only undo still clobbers a collaborator's same-key write.|
|Loro undo docs|docs|`ad299a7d1d9c18e54b17ea3e8b70f0ec` [link](https://loro.dev/docs/advanced/undo)|read|RQ1, RQ2: mergeInterval merges edits within 1000 ms; undo is local-only; a conflicting remote import can end a manual group.|
|Nuss 2016|thesis|`4364947b664546b69c4f5dbea2632610` [link](http://scholarsarchive.byu.edu/etd/5875)|read|RQ1, RQ2, RQ3, RQ4: 70% of 20 CAD participants preferred local undo; global never above 25%; 40-45% wanted confirmation.|
|Replit checkpoints and rollbacks docs|docs|`2f3f6ad7ee7386e1a9e82db219a7e5f3` [link](https://docs.replit.com/features/version-control/checkpoints-and-rollbacks.md)|read|RQ1, RQ2, RQ3: Agent-chosen milestones with AI-written descriptions and roll-forward; rollback removes all changes after the point.|
|Roblox ChangeHistoryService docs|docs|`87f6ffae49f97e02b170ccb4be8616fb` [link](https://create.roblox.com/docs/reference/engine/classes/ChangeHistoryService)|read|RQ1: TryBeginRecording then FinishRecording with Commit, Cancel or Append: an explicit begin-and-finish pair; one open recording per plugin.|
|Roblox Team Create docs (2020 archive)|docs|`ad9ef400c76ac4ea35649b9787a97d34` [link](https://web.archive.org/web/2020/https://developer.roblox.com/en-us/articles/Team-Create)|read|RQ1, RQ2: Per-object undo restores the pre-edit value and discards later edits by others; the naive overwrite policy (2020 archive).|
|StraySpark: Ctrl+Z Is Not a Rollback Strategy|vendor blog|`a3ae9bd52b836598a3c38f33793af25f` [link](https://www.strayspark.studio/blog/undo-ai-agent-changes-unreal-effect-journal-rollback)|reported|RQ3, RQ4: Unreal transactions revert object state, not existence; proposes undo_recorded=false so a missing undo entry is never silent.|
|Tag1 TagTeamTalk #001 transcript|vendor blog|`067f9a5cb6c60f69a3e1790363d36420` [link](https://web.archive.org/web/20251015183337/https://www.tag1.com/tag1-team-talks/deep-dive-real-time-collaborative-editing-solutions-tagteamtalk-001-0/)|read|Background: A panelist says most users reject undoing content they did not create; anecdotal.|
|Taskade: When AI Agents Join Your Multiplayer Document|vendor blog|`5658905c8f6c0d807653c6f4e9cb1858` [link](https://www.taskade.com/blog/agents-multiplayer-ot)|read|RQ1, RQ2, RQ3: Vendor claim: operations tagged human or agent, grouped by intent with one-step undo; no refusal rule.|
|tldraw History docs|docs|`7e4186d6d2bd74fb9c0b927a14d3e708` [link](https://tldraw.dev/sdk-features/history)|read|RQ1, RQ2: mark, squashToMark and bailToMark batch a complex interaction into one undo step; only user-sourced changes undo.|
|Unity Undo class docs|docs|`dd9dcba9e6fda218bf6052a14d061916` [link](https://docs.unity.com/en-us/engine/6000.6/script-reference/unityeditor/undo)|read|RQ1: Input events split groups by default; IncrementCurrentGroup and CollapseUndoOperations give explicit boundaries.|
|Unity Undo.CollapseUndoOperations docs|docs|`9b7912f7440678eb7213e097bbf6136c` [link](https://docs.unity.com/en-us/engine/6000.6/script-reference/unityeditor/undo/collapseundooperations)|read|RQ1: Retroactively collapses everything since a remembered group index into one named step, the closest analogue to group_turn.|
|Unity Undo.RecordObject docs|docs|`b8cea4a92120a10b36127c76b9bd49d6` [link](https://docs.unity.com/en-us/engine/6000.6/script-reference/unityeditor/undo/recordobject)|read|Background: Unity infers the inverse as a before/after diff at end of frame; the Dark Factory declares it per operation.|
|Unreal Engine 5.1 Multi-User Editing overview|docs|`8a706debf9ba9610f5c9758afc6337c7` [link](https://dev.epicgames.com/documentation/en-us/unreal-engine/multi-user-editing-overview-for-unreal-engine/?application_version=5.1)|read|RQ1, RQ2: Same page for 5.1: own history only; it does not say what follows another user's edit.|
|Unreal Engine 5.4 FScopedTransaction API|docs|`93f1e17ce79a60da91bb8cf816cbbb3c` [link](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Editor/UnrealEd/FScopedTransaction?application_version=5.4)|read|RQ1: Caller-owned RAII scope with the name supplied at the boundary; same shape as Houdini's with-block.|
|Unreal Engine Multi-User Editing overview|docs|`1647dff4639c912749cba8f50a8ab178` [link](https://dev.epicgames.com/documentation/en-us/unreal-engine/multi-user-editing-overview-for-unreal-engine)|read|RQ1, RQ2: Epic's level editor undoes own history only; no cross-user undo, and same-property conflicts unstated.|
|Unreal Undo/Redo transaction deep dive (Epic forum)|forum|`584156467ace61e2a2623667059081fb` [link](https://forums.unrealengine.com/t/deep-dive-on-unreal-undo-redo-transaction-system/2688186)|reported|Background: Unreal stores the delta between state captures at Modify() and transaction end; hooks fix untracked data.|
|US10261756B2 reference invalidation patent|patent|`59f133e7ed9cb634d800db1a17a02eda` [link](https://patents.google.com/patent/US10261756B2/en)|reported|Background: Before reversing an operation, check whether another client's operation would make the reversal create an invalid reference.|
|US6523134B2 selective undo patent (IBM)|patent|`f047f783134691ea3f617d348c78c7f2` [link](https://patents.google.com/patent/US6523134B2/en)|reported|Background: Undoing one recorded action falls back by tiers: undo alone, undo dependents too, else roll back to that point.|
|VS Code review and revert agent changes docs|docs|`66b63b61765b1692ff326f6a8c7ec892` [link](https://code.visualstudio.com/docs/agents/run/review-code-edits)|read|RQ1, RQ2, RQ3: Keep or Undo per change, file or all, plus per-request checkpoint; terminal commands stay unreversed.|
|Windsurf Cascade checkpoints docs|docs|`6d748edec83f9c90feff32307c79bd54` [link](https://docs.devin.ai/desktop/cascade.md)|read|RQ1, RQ3: Prompt-level and person-named checkpoints; its revert is irreversible, the failure Replit's roll-forward avoids.|
|Yjs Y.UndoManager docs|docs|`548698ab6c1236b1b1fa46f861e8ddcf` [link](https://docs.yjs.dev/api/undo-manager)|read|RQ1, RQ2: captureTimeout merges edits within 500 ms; trackedOrigins scopes undo to chosen actors.|
|Zed Agent Panel docs|docs|`1011f8b64cc5fe19a25e4efe782d0331` [link](https://zed.dev/docs/ai/agent-panel.md)|read|RQ1, RQ2, RQ3: Accept or reject per hunk or whole set; separate Git worktrees keep agent and person edits apart.|
|Zed: How CRDTs make multiplayer text editing part of Zed|vendor blog|`c9bfa5a5a6b6aa3699a77d07d6c7190f` [link](https://zed.dev/blog/crdts)|read|RQ1, RQ2: Undo map over an append-only log: the log stays immutable and only the user's own operations undo.|
|aider /undo and auto-commit source|code|`code-aider-5dc9490`|read|RQ1, RQ2, RQ3: /undo refuses when HEAD is not aider's own commit, files are dirty or the commit was pushed.|
|bevy_editor_prototypes bevy_undo source|code|`code-bevy_editor_prototypes-55723a3` [link](https://github.com/bevyengine/bevy_editor_prototypes/blob/55723a3e74fc43af0ffbf8b62ca5dcf4b81385fe/crates/bevy_undo/src/lib.rs)|read|RQ1: Groups by quiet frame burst: cheap but unnamed, with no owner or refusal, a negative example.|
|Blender undo stack source|code|`code-blender-d385c76` [link](https://github.com/blender/blender/blob/d385c767df587029aa78edf83a1a8bb939d8bb6d/source/blender/editors/undo/ed_undo.cc)|read|RQ1: group_begin/group_end mark inner steps to skip, grouping without reordering; a missing group_end merges all later steps.|
|Fyrox editor CommandStack and CommandGroup source|code|`code-fyrox-1ad021a` [link](https://github.com/FyroxEngine/Fyrox/blob/1ad021a8daa9a3933a605936c85920ad151e14d7/editor/src/command/mod.rs)|read|RQ1: CommandGroup bundles commands into one undo entry on a Rust command stack close to the Dark Factory's own.|
|Godot editor undo manager source|code|`code-godot-7c97c29` [link](https://github.com/godotengine/godot/blob/7c97c297793ce4711679491d34693a5719a79ebe/editor/editor_undo_redo_manager.cpp)|read|RQ1: Merges an action into the previous one only within 800 ms and with the same name.|
|tldraw HistoryManager source|code|`code-tldraw-98c344c` [link](https://github.com/tldraw/tldraw)|read|RQ1: HistoryManager mark, squash and bail form an API for an agent turn; a forgotten mark merges two interactions.|
|Yjs UndoManager source|code|`code-yjs-15b0a62` [link](https://github.com/yjs/yjs)|read|RQ1, RQ2: UndoManager keys undo by trackedOrigins, merges within captureTimeout, and skips a conflicting redo silently.|
|Ousterhout, A Philosophy of Software Design (2nd ed.)|book|`ousterhout_philosophy_of_software_design_2nd`|read|RQ3: History mechanism, per-kind actions and grouping policy are separate layers; policy belongs in high-level interface code as fences.|
|r/cursor: restoring a checkpoint after further edits|forum|`reddit-cursor-1mwpzkv` [link](https://www.reddit.com/r/cursor/comments/1mwpzkv/what_happens_if_you_need_to_restore_a_checkpoint/)|reported|RQ2, RQ3, RQ4: A user wants one earlier checkpoint undone but later edits kept; both replies point to Git.|

**Prior art for the ideas.** Captured during the convergent pass; the relevance names the idea in "Ideas" or "Dropped ideas" it bears on.

|Source|Kind|Where from|Confidence|Relevance|
|---|---|---|---|---|
|BlkDem blender-mcp README|docs|`903d53443cfaf7ba6854f39c890eb731` [link](https://github.com/BlkDem/blender-mcp)|read|Idea 1: restores recorded state because Blender's undo history cannot be read from Python.|
|Claude Code permission modes docs|docs|`c8a9703cc1eb71bab49026e03a5da894` [link](https://code.claude.com/docs/en/permission-modes)|read|Dropped approval guard: modes and ask rules gate by tool, not by whether undo can give it back.|
|cline responses.ts|code|`b7bb4690cfd83394d526aa191328ad08` [link](https://github.com/cline/cline/blob/d92f9393acec3f7f6d8b2bdf59f2c7e1d23ccb87/apps/vscode/src/core/prompts/responses.ts)|read|Idea 4: the agent is told the person edited its proposed content and to use it as the new baseline.|
|CoplayDev/unity-mcp ManageEditor.cs|code|`a4d7afc26b251970f2a01a63ddc39a7a` [link](https://github.com/CoplayDev/unity-mcp/blob/19b66ecef4ac3a9be22a7a62ea21accb975c39e7/MCPForUnity/Editor/Tools/ManageEditor.cs)|read|Idea 6: the MCP undo is a blind Undo.PerformUndo() that can take the person's change.|
|MCP schema 2025-06-18|docs|`9908b1e5c59be54285dc42becb252f78` [link](https://modelcontextprotocol.io/specification/2025-06-18/schema)|read|Ideas 2, 6: the protocol has no undo or transaction primitive, only advisory hints and elicitation.|
|nsgo-dev/game issue #1011|issue|`73efe81613fb7121d7163bc743d74ce1` [link](https://github.com/nsgo-dev/game/issues/1011)|reported|Ideas 1, 3, 4: an AI-first game editor holds a turn until Keep; the agent reads which changes were reverted.|
|nsgo-dev/game PR #1219|issue|`398cf695016abee3a656a7b8319bd6c3` [link](https://github.com/nsgo-dev/game/pull/1219)|reported|Ideas 1, 4: a kept turn is one history command tagged as the agent's; read-only turn status.|
|paper-lite PR #56|issue|`7d2684670b0199aac7c1e0477fff90bb` [link](https://github.com/rocketonthemoon/paper-lite/pull/56)|reported|Ideas 2, 5, 6: field-level selective revert that keeps others' later edits and reports them as kept.|
|Privatrak: We gave our MCP server an undo button|vendor blog|`255be6b6cfeaa5bbb88e2aff873b0fba` [link](https://dev.to/quentin_wendegass/we-gave-our-mcp-server-an-undo-button-2mah)|reported|Idea 2: per-change checks, skip-and-report on failure, and a dry run that is the real undo rolled back.|
|Rhino 9 Undo, UndoSelected and UndoMultiple docs|docs|`2b23a27866969882a917d233e62dea19` [link](https://docs.mcneel.com/rhino/9/help/en-us/commands/undo.htm)|read|Dropped regional Cmd+Z: UndoSelected reverses recent changes for a selected object only.|
|Roblox Assistant for Studio docs|docs|`e9cd9371601c85d810ebbcd14e08ba2e` [link](https://create.roblox.com/docs/assistant/guide)|read|Ideas 3, 6: Planning Mode has editable steps, an explicit approval gate and checkpoints.|
|Roblox DevForum: Assistant updates, 2025-03-17|forum|`80035ceff5199b4a3423482c9f115458` [link](https://devforum.roblox.com/t/3555172)|reported|Ideas 1, 2: Assistant changes undo with Cmd+Z; a rejected change cannot be got back.|
|Roblox DevForum: Planning Mode, 2026-04-16|forum|`3a8b197f22b382bd9befde52611256ea` [link](https://devforum.roblox.com/t/4580715)|reported|Idea 3: an editable plan with a Build gate and per-session checkpoints.|
|Roblox Studio MCP server docs|docs|`e67d90c13e211bb976d08b4d9139288f` [link](https://create.roblox.com/docs/studio/mcp)|read|Idea 1: the official tool set has no undo or checkpoint tool; save notes reach version history.|
|s&box Undo System docs|docs|`9ddc1b70c19b26d5e3794433cac51e42` [link](https://sbox.game/dev/doc/editor/undo-system)|read|Idea 5: an undo scope is told which objects it will modify, a footprint used for capture, not refusal.|
|SmartUndo+ for Blender, trade press article|press|`c118d0e175fb5606a947bee1644931bb` [link](https://digitalproduction.com/2026/07/30/smartundo-makes-blender-undo-excellent)|reported|Dropped regional Cmd+Z: a second chord undoes only the selected object or node tree.|
|tomyud1/godot-mcp undo-tools.ts|code|`3a2a1ee4eb3fe3f2a3503ca361e2f64e` [link](https://github.com/tomyud1/godot-mcp/blob/main/mcp-server/src/tools/undo-tools.ts)|read|Ideas 2, 3: the AI's changes sit outside the editor's Ctrl+Z; atomic pending rollback with a preview.|
|ue-mcp checkpoints docs|docs|`75ded08ca866d4c7c081cfb55af729a1` [link](https://github.com/db-lyon/ue-mcp/blob/main/docs/checkpoints.md)|read|Ideas 1, 2, 5: begin and end transaction as one undo step; restore refuses files edited outside.|
|ue-mcp PR #1520: editor(batch)|issue|`f5b9532809183badb9a889b560a7db9d` [link](https://github.com/db-lyon/ue-mcp/pull/1520)|reported|Idea 2: a batch is refused whole before anything runs, with a verdict per step.|
|Unity Assistant checkpoints docs|docs|`693085642c420203709f93ee023f7491` [link](https://docs.unity3d.com/Packages/com.unity.ai.assistant@2.0/manual/checkpoints.html)|read|Ideas 1, 2: per-prompt checkpoint restore reverts the person's edits too, with only a confirm prompt.|
|Unity Assistant permissions docs|docs|`6ef64a002ccbc105367d8a98ce8bd01f` [link](https://docs.unity3d.com/Packages/com.unity.ai.assistant@2.0/manual/preference.html)|read|Dropped approval guard: per-operation Allow, Ask Permission or Deny, keyed on the operation class, not on undoability.|
|Unreal Engine 5.8 release notes|docs|`8853efe45c002f7e2540caff055d6d2a` [link](https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-5-8-release-notes)|read|Dropped another layout: PCG manual edits persist on top of regenerated data.|
|Unreal Engine PCG overview docs|docs|`5453a853362b88bb1add2ad6f9719d78` [link](https://dev.epicgames.com/documentation/unreal-engine/procedural-content-generation-overview-for-unreal-engine)|read|Dropped recipe status: a PCG component seed changes the random result; determinism and data-override tabs.|
|Unreal MCP in Unreal Editor docs (5.9, Experimental)|docs|`44c69d5c55ccef779f4581c1b1c46691` [link](https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-mcp-in-unreal-editor)|read|Ideas 2, 6: AI access modes gate reads and writes; the page says nothing about undo.|

**Acquired, not yet read:** none.

**Could not obtain** (kept at screening, not read):

- *A General Multi-User Undo/Redo Model* (1995), `10.1007/978-94-011-0349-7_15`.
- *Rollback Is Not Undo: Path-Dependent Failures in LLM-Arbitrated Network Control* (2026), `10.1109/infocom59046.2026.11571400`.
- *VRGit: A Version Control System for Collaborative Content Creation in Virtual Reality* (2023), `10.1145/3544548.3581136`.
- *Point of no Undo: Irreversible Interactions as a Design Strategy* (2023), `10.1145/3544548.3581433`.
- *A Selective Undo/Redo Algorithm for Dependency-Constrained Operation Histories Based on Change Propagation* (2026), `10.1145/3832783.3837482`.
- *Using Task Models for Cascading Selective Undo* (2006), `10.1007/978-3-540-70816-2_14`.
- *3DFlow: continuous summarization of mesh editing workflows* (2015), `10.1145/2766936`.
- *Nonlinear revision control for images* (2011), `10.1145/1964921.1965000`.
- *SceneGit: a practical system for diffing and merging 3D environments* (2019), `10.1145/3355089.3356550`.
- *Detecting local undo conflicts in multi-user CAD* (2016), `10.1080/16864360.2016.1168217`: home-still stored a different paper under this DOI; its conference version `10.14733/cadconfp.2015.470-474` returned an HTML page, not a PDF.
- Su, Paris & Durand 2009 (graphical history): the download returned HTTP 429.
- The r/cursor thread in the table was read in a browser but could not be captured into home-still.

## What the sources say

Strength labels: **measured** (a study with participants, logs or a benchmark), **reasoned** (a formal model, a design argument, or documented product behaviour), **reported** (forum, issue, vendor marketing, patent).
Short names resolve through the Sources table.
Every quotation passed home-still's `cite` against the stored document; the identifier after it is the home-still `doc_id`.

### Across all four questions

1. No source measured undo with an AI agent as the second actor in an editor with a person in the loop.
   Every human number below comes from human peers or a single user, and every agent number from a harness with no person in it.
2. Grouping and scope are two separate decisions.
   The outer edge of a unit is an explicit, declared boundary: a transaction, a turn, a delegated task.
   Time only merges one gesture inside it.
   Actor decides which units an undo may reach.
3. The hard problem is not the size of the unit but what happens when an undo meets a later edit by someone else: refuse, mask, cascade or overwrite.
   Products mostly overwrite or skip silently; the research says ask, or at least tell.
4. People want two levels: a small step for the frequent small backtrack, and a named larger unit for a delegated change, with a way to peel members off the larger one.

### RQ1. Where should an undo unit end?

**Answer.** Layered.
The outer edge is an explicit intent or transaction boundary, declared by the actor or the runtime.
Time is a narrow inner rule, 300 ms to 2 s and always paired with a same-target or same-name condition, for merging one gesture.
Actor is a scope filter over units, not a boundary.

**Agreed.**

- Every engine that exposes grouping does it with explicit begin and end, mark or collapse calls, not time: Unity `CollapseUndoOperations`, Roblox `TryBeginRecording` and `FinishRecording`, Unreal `FScopedTransaction`, Houdini `hou.undos.group`, tldraw marks, Godot nested actions, Blender `group_begin` and `group_end`, Fyrox `CommandGroup` (reasoned: docs and source).
- Time constants merge gestures only: Godot 800 ms plus same name, Yjs `captureTimeout` 500 ms, Loro `mergeInterval` 1000 ms, Chen 2016 500 ms or same region, Azurite 2 s and never across lines, RaivenTracks 300 ms (reasoned; tuned by pilot or observation, never tested).
- The agent-transaction literature puts the unit at intent: Atomix's "smallest unit of agent intent whose effects must settle together", Cordon's delegated task, and the steps of SagaLLM and of Sagas that "should not be left unfinished" (reasoned for the definition; Atomix and Cordon measure their mechanisms, not the unit size).
- Hierarchical command objects: only the top-level semantic command is listed and undone, and its children go with it (Myers & Kosbie 1996, Edwards 2000, Sun 2002; reasoned).

**Conflicts.**

- Display chunking uses 5 s and 30 s windows (Heer 2008, measured on 20,192 logged actions) but leaves Undo per action.
  These windows answer "what does the strip show", not "what does Undo take".
- Chen 2016 groups by working-region overlap; Liu 2020 finds region overlap and image difference are not useful predictors (both measured, in different settings).
- Who places an agent's boundary: the person's prompt (Claude Code, Windsurf, VS Code), the system per tool use (Cline), or the agent's own judgement (Cursor, Replit).
  No source compares them.
- Whether a group should undo whole: Edwards and Prakash & Knister 1992 say undo must not stop inside a transaction.
  Myers 2015, VS Code's per-change Undo and Ink & Switch's Patchwork show demand for peeling one member off.

**Measured.**
Automatic segmentation works at the low level and fails at the high level: Cohen's kappa 0.77 for low-level chunk starts, "little agreement" for high-level chunks, segmenter precision about 0.51 (Liu 2020, 16 sessions, 13 people).
Backtracking happens about once every six minutes, and its size spans one character to thousands (Yoon & Myers 2014, 1,460 hours, 21 programmers).

**Unanswered.**
No source measured the right size of an agent-turn unit with a person in the loop, the gaps between an agent's operations, or an explicit turn boundary against an inferred one on the same stream.

**Quotes.**

- "The integration layer chooses transaction granularity: the smallest unit of agent intent whose effects must settle together under one invariant" (Atomix, `10.48550_arxiv.2602.14849`).
- "a new task or a change in delegated authority creates a new transaction scope" (Cordon, `10.48550_arxiv.2606.17573`).
- "The UndoManager merges edits that are created within a certain `captureTimeout` (defaults to 500ms)." (Yjs docs, `548698ab6c1236b1b1fa46f861e8ddcf`).
- "However, undo events will step back through each of the chunked actions individually." (Heer 2008, `10.1109_tvcg.2008.137`).
- "for high-level chunks there was little agreement even between human coders" (Liu 2020, `10.1145_3313831.3376152`).

### RQ2. Selective undo with another actor's edits interleaved, and when to refuse

**Answer.** Per-actor (local) undo is the best-supported default, conditional on how closely the actors work together.
Local undo is well defined only when the interleaved edits commute.
When they do not, there are three policies: refuse until the blocker is undone, mask so the undo has no visible effect, or cascade so dependents go too.
The only measured preference among them (cascade, 18 of 28) comes from a single-user task.
A refusal should rest on a dependency test, but exact dependency detection is costly and noisy, and a refusal that is too strict frustrates.

**Agreed.**

- People expect to undo their own last action, not the globally last one (Prakash & Knister 1992 and 1994, Ressel 1996, Sun 2000; reasoned).
- A measured study confirms it for human peers: 70% of 20 CAD participants preferred a local stack in both scenarios, all 12 people on three-person teams chose local, and global undo never drew more than 25% (Nuss 2016, measured).
- Products ship local undo: 5 of 6 tested collaboration apps (Google Sheets, Slides, Excel Online, PowerPoint Online, Figma), with Miro blocking undo whenever another user's operation on the same register arrives (Stewen & Kleppmann 2024, measured by hand testing).
  Loro, Zed, Excalidraw, Liveblocks, tldraw, Yjs `trackedOrigins` and Unreal Multi-User Editing state the same (reasoned: docs).
  Roblox Team Create is the exception: per-object undo that discards later edits by others (2020 archive).
- Local undo still clobbers a collaborator's later write to the same key (Loro issue #1229; Yjs silently skips a conflicting redo; reported and code read).
- Local equals global exactly when the intervening actions commute; otherwise there is "no sensible meaning", and the system should ask (Abowd & Dix 1992, reasoned).

**Conflicts.**

- Scope: Nuss (local); Seifried 2012 (regional matched expectations in 86% of cases, personal 47%, global 22%; n=23); Rasch 2024 (a shared world stack rated highest on social connection, IOS 4.48, when two people built one tower; n=32).
  The settings differ in how closely people work and how their objects depend on each other, not in technology.
- Policy: refuse (Prakash & Knister), mask (Sun 2000 and 2002, Chen & Sun 2001), cascade (Cheng 2014, Lv 2019, Yu 2019), shadow (Ressel 1996), rewind-repair-replay (Brown & Patterson 2002), and compensation that neither restores the old state nor notifies readers (Sagas 1987).
  Masking is well defined for text and per-attribute graphics; structure edits and feature trees need dependency knowledge and cascade.
- Partial undo of a multi-step action: Prakash & Knister 1992 wanted all-or-nothing.
  Their DistEdit later shipped partial undo because users "would prefer to undo as much of a complex change as possible than to undo none of it".
  Edwards argues a history may be entered or left only at transaction boundaries.
- Silent no-op against loud refusal: Figma, Google Slides and Excalidraw skip an undo with no visible effect, and Yjs falls through to the next item; Sun and Berlage say the user must be told.

**Measured.**

- Cass 2006: "1 used linear, 7 used script, and 18 used cascading" (n=28, paper task, one actor).
- Azurite (Yoon & Myers 2015) offers three outcomes on a conflict (undo the conflictee and keep the conflictor, undo the conflictors too, cancel) and halved backtracking time, 386.3 s against 768.8 s (n=12, p<0.01).
- Nuss: 40% and 45% of participants expected a confirmation before undoing something another feature depends on.
- Agent harnesses, none with a person's interleaved edits:
  - ACRFence: "all 10 checkpoint-restore trials produced duplicate commits (100%), while a no-checkpoint baseline produced none (0/10)".
  - Atomix leaked 0 of 500 irreversible sends, against 400 for saga compensation and 200 for checkpoint-replay.
  - AgentRewind: 87.8% against 62.2%, and 43.9% without environment rewind.
  - Cordon: rollback 4.17 ms median with 0 residual deltas, against 73 for `git restore`.

**Unanswered.**
No study has an agent as the interleaved actor.
No study compares refuse, mask and cascade with the same task and people.
No source gives a false-positive rate for dependency detection; Aquamarine abandoned exact detection for "too many false positives".
Nothing measures what refusing too much costs, beyond DistEdit's authors' report.

**Quotes.**

- "situations in which result commutativity holds allow for local undo to be implemented as global undo" (Abowd & Dix 1992, `10.1016_0953-5438(92)90021-7`).
- "an operation cannot be undone if it conflicts with a later operation, unless the later operation is undone first" (Prakash & Knister 1992, `10.1145_143457.143527`).
- "users tend to get frustrated when they are unable to undo something that they consider to be undoable" (Prakash & Knister 1994, `10.1145_198425.198427`).
- "Out of all the participants, 70% preferred a local undo stack in both scenarios" (Nuss 2016, `4364947b664546b69c4f5dbea2632610`).
- "Unfortunately, since it is not entirely clear what the user wants, it would not be appropriate for the system to choose arbitrarily without user intervention." (Azurite, `10.1109_icse.2015.43`).
- "no effort is made to notify or abort transactions that might have seen the results of" (Sagas, `10.1145_38713.38742`).
- "1 used linear, 7 used script, and 18 used cascading" (Cass 2006, `10.1145_1182475.1182478`).

### RQ3. What a person needs to trust, inspect and revert an agent's multi-step change

**Answer.** Three things.
First, the plan before the agent acts, with approval at a step size the person can tune.
Second, review at more than one scope (item, turn, task), with provenance.
Third, a revert that is atomic or says exactly what it did not do, names what it will overwrite, leaves the person's own edits alone or names them, and is itself undoable.
The first two have small measured studies behind them; the third rests almost entirely on reported failures.

**Agreed.**

- Plan first, then per-action approval, kept 8 LAVE users in control (measured, n=8).
  Magentic-UI participants found the approval requests excessive and long task histories overwhelming (measured, qualitative, 12 participants).
  Cordon priced approve-all at +22.7% task time (measured, no people).
- Every agentic dev tool offers at least two review scopes: VS Code (per change, file, all; per-request checkpoint), Codex (whole diff, file, hunk, "Last turn"), Zed (hunk or whole set) (reasoned: docs).
- Per-item revert plus a whole-change revert beats an all-or-nothing restore.
  In Semantic Commit, ChatGPT Canvas rewrites forced version-history restores in 8 instances across 6 of 12 participants (measured).
  In EvoGraph, prompt-sized branching checkpoints lowered frustration, and a linear revert was called destructive (measured, n=20).
- The failure people meet is a revert that silently takes their own edits: Cursor, Junie, Replit, and a Claude Code rewind that overwrote about 20 hours of edits after reporting failure (all reported).
- Revert limits should be stated: Unreal transactions revert object state, not existence (StraySpark, reported); aider's `/undo` refuses when HEAD is not its own commit or files are dirty (code read).

**Conflicts.**

- Approve first or roll back later: LAVE and Magentic-UI gate before each action; Cline argues cheap rollback replaces approval; Semantic Commit users split 6 to 5 between checking impact first and changing first.
- Who draws the checkpoint boundary (prompt, tool use, agent milestone); no comparison exists.
- Selective undo is wanted, and faster, where it shows conflicts and asks (Azurite, Aquamarine), and worse where it works one object at a time with no dependency tracking (Rasch).
- Graph against linear history: EvoGraph users liked the graph; CAD forum users find long branch trees unreadable (Cheng 2023, reported).

**Measured.**
A person's undo is a cheap usability signal: undo and erase events covered 23 of 25 severe problems in SketchUp, and 58% of unreported problems went unreported because users blamed themselves (Akers 2009, n=35).
Clustered, filterable history speeds navigation (Chronicle n=8, MeshFlow n=8, Chen 2016 n=6, F=11.83, p=0.0014), but none of these tested a revert.

**Unanswered.**
No source measured a person reviewing or reverting a multi-step agent change in any editor.
No study tests preview-before-restore, or telling the agent what was reverted, with a person in the loop.
Ownership marks (Tanagra) were never user-tested.

**Quotes.**

- "Rather than batch approval, each action is sequentially approved by the user." (LAVE, `10.1145_3640543.3645143`).
- "many qualitative study participants found it overwhelming to monitor or review long task histories to understand what happened or troubleshoot" (Magentic-UI, `10.48550_arxiv.2507.22358`).
- "When you clicked revert/restore checkpoint, the code went back to the state before your manual changes." (Cursor forum, `99f09380aa98e01fdeaf4dafb043bb8d`; reported).
- "If a rewind says it can't be done, nothing on disk should change." (Claude Code issue, `e1ca01afd6c3cec35566b25de84cfce9`; reported).
- "decisions made by the human cannot be overridden by the system" (Tanagra, `10.1145_1822348.1822376`).

### RQ4. Grouping that is too coarse or too fine

**Answer.** No source varies the grouping of an agent turn and measures what people then do.
The proxies agree on both failure modes.
A unit that sweeps in unrelated work, or can only be reverted whole, produced errors and forced restores.
A unit of one object, one stroke or one approval raised load and frustration, and users asked for grouping.
What the evidence supports is two levels, not a best size.

**Agreed.**

- Too coarse: 23 of 26 clustering errors were ambiguous or too-large clusters (Seifried 2012, n=18); whole-document rewrites forced 8 restores (Semantic Commit, n=12); commit-sized units are too coarse for AI edits (EvoGraph, n=8 interviews and n=20 study); Azurite's authors expected coarse operations to cause "many more regional conflicts".
- Too fine: one-object selective undo raised frustration and lowered recovery ratings, raw TLX 42.0 against 34.4 and 34.6 (Rasch 2024, n=32).
  Azurite users called the timeline rectangles "too fine-grained".
  Photoshop users' main request was "a way to group actions" (Myers 2015, n=8 and 9).
  More than half of 12 Dwell-and-spring participants wanted several undos in one step.
- Small backtracks dominate, with a long tail: the most common size is 10 to 49 characters, 9.5% are selective, and 63% of the selective ones were redone by hand (Yoon & Myers 2014).

**Conflicts.**

- The direction of the error depends on the setting: Seifried's coarse clusters failed, while Rasch's coarse WorldUndo won when the pair worked together and drew "the other player disturbed me" ratings when they worked apart.
- Over-segmentation is cheap for navigation (Liu, Chen) and costly for undo, where a wrong merge swallows an edit; the second half is argued, not measured.
- Confirmation before undo: 40–45% expect it (Nuss), one Semantic Commit participant called it overkill, and DistEdit's authors call refusal frustrating.

**Unanswered.**
No study compares a two-level undo (operation and turn) with a single unit on any outcome.
None studies partial revert of a delegated change after the person edited near it.
None counts how many operations an agent turn contains.
None studies world or level editing with an agent.

**Quotes.**

- "Ambiguous clusters / too large clusters (occurred 23 times)" (Seifried 2012, `10.1145_2207676.2208690`).
- "In the task, undoing only single building blocks was rarely beneficial, as the tower more often collapsed as a connected bigger structure." (Rasch 2024, `10.1145_3613904.3642864`).
- "the granularity of the traditional version control commits does not align with the small, frequent, and sometimes temporary changes made when using an AI assistant" (EvoGraph, `10.48550_arxiv.2604.18883`).
- "The main requested feature was a way to group actions." (Myers 2015, `10.1145_2702123.2702543`).
- "9.5% of all backtracking instances were selective" (Yoon & Myers 2014, `10.1109_vlhcc.2014.6883030`).

## The Dark Factory today

Read from `dark-incorporated/bevy_dark_factory` at main `63ab4f724a` through the GitHub API, because a loop owns the local clone.
Paths are under `crates/bevy_dark_factory/src/` unless named otherwise.
**Read, not run**: every behaviour below comes from source and doc comments, and nothing was built or executed.

**What already matches the evidence.**

- One way to change anything: a typed operation in one registry, dispatched by keys, menus and the agent alike, each declaring an undo strategy (`Undo::None`, `Undo::Inverse`, `Undo::Snapshot`; `docs/PROJECT.md` §2–3).
- The oplog is append-only: an undo is a new line naming the line it undoes, and a change is a chain that is in effect or not (`ops.rs:8951-8966`, `undo_target`).
- The agent's untargeted undo takes back the agent's own newest change and never a person's; naming a line by id is not filtered (`ops.rs:9033-9040`, decided in issue #530).
  That is the local undo every human-peer study preferred.
- The hand-back (`blueprint_present`) names the operation ids a task covers, and E-071 collapses them into one `Undo::Group` (`editor.rs:390-448`, `group_turn`; boundary at `editor.rs:397-400`).
  That is the explicit, declared boundary every engine API uses.
- A refused undo names the newest blocker, its operation and its source, and offers "Undo `<blocker>` first, or leave `<line>` as it is" (`ops.rs:9112-9128`): Prakash & Knister's refuse policy, with an explanation.
- Undo all walks the turn newest first, stops at the first refusal and says where it stopped (`present.rs:929-961`).
- The agent can take back a whole turn (E-076, `turn: true`), and one redo puts it back (`editor.rs:539-562`, `record_undone_turn`).
- The agent reads the person's hand-back answer ("kept", "undone", or why the undo stopped) from `blueprint_state`'s `presentation.answer` (`docs/mcp-tools.md:159`).
- Working a note, an agent's write is fenced to the note's area, and removing a piece a person placed needs `note_ask` first (`docs/mcp-tools.md:130`): an ownership pin like Tanagra's, for notes only.
- A drag-adjust coalesces into one entry through a deliberately narrow classifier, because "a wrong `Some` would swallow an edit an author wanted back" (`build.rs:1087-1096`).
- The turn ledger (DL-01, DL-02) records every agent turn from "the agent's first write operation after its last hand-back, to its hand-back", with before and after pictures, and stores the person's Keep or Undo all as a gold verdict (`turn_ledger.rs:1-18`, `:741-748`; `present.rs:955-965`).
  That is Akers' undo-as-usability-signal at turn granularity.

**Where it departs** [INFERENCE from the code, not run].

1. **The boundary arrives late.** The turn ledger knows when a turn begins (`TurnLedger::turn_begins`, called before the first write), but the undo stack learns of the turn only at hand-back.
   Before hand-back the person's Cmd+Z sees loose entries; operations after the hand-back start a new, ungrouped turn (`editor.rs:406-421`).
2. **Grouping reorders history.** `group_turn` drains the stack, takes out the turn's entries and pushes the group on top, so a person's edit made during the turn ends up below it (`editor.rs:422-445`).
   A person's next Cmd+Z then takes the agent's turn before the person's own newer edit.
   Abowd & Dix: reordering is sound only when the actions commute.
3. **A group undo is partial.** `undo_target` blocks a change when any newer change is in effect anywhere on the same map; only library changes are scoped per piece (`ops.rs:9102-9117`).
   In the `Undo::Group` arm of `apply`, a refused member "contributes nothing", the group counts as done if any member applied, and the inverse omits the refused members (`editor.rs:14055-14079`).
   The refusal is named once in the status line ("cannot undo …", `editor.rs:14325-14335`), but the person is offered no choice.
   Put with point 2: in the real-time order a1, h1 (the person's), a2, a3, Cmd+Z undoes a3 and a2, refuses a1 because h1 is newer, and pops the group, so a1 stays in effect with no stack entry and is reachable only by id.
   Without the reorder, three presses would walk a3, a2, h1, a1 and refuse nothing: the grouping itself makes the refusal.
   Undo all, the agent's turn undo (`ops_brp.rs:3071-3085`) and `jump` (`editor.rs:13866-13925`) stop at the first refusal and keep what they undid, so four walkers apply two different partial rules.
4. **The conflict test is the whole map.** Any later edit anywhere blocks, the rule DistEdit's authors found "too restrictive in practice", and only the newest blocker is named.
   A second guard compares the operation's declared state (`state_of`) with what the line left, but only for operations that declare one (`ops.rs:9136-9160`).
   Every agent `plan_set` is itself a logged map-scoped line (`ops_plan.rs:161`), so a plan update newer than the turn's last placement, and not listed in the hand-back, should block the undo of every older member [INFERENCE, not run].
5. **Actor scope is split.** The agent's untargeted undo is local; the person's Cmd+Z is global ("One undo history", `docs/PROJECT.md:80`), the model human-peer studies rated lowest, though Rasch found a shared stack best under close collaboration.
6. **There is no peel.** A person can keep or undo a whole turn, or undo single members through the Agent workspace's per-row Undo (`present.rs:979-991`), but the map-wide guard allows that only from the newest down.
7. **The agent hears only about Undo all.** A person's later Cmd+Z of a grouped turn, or of single agent entries before hand-back, reaches the agent only as a changed `undo_next` and undo depth, or as undo lines it would have to find in `blueprint_read_oplog` without being told to look.
8. **The ledger sees only some undos.** After a Keep, a person's own undo or edit of the kept turn's pieces within 30 minutes becomes a gold `revised` label (`turn_ledger.rs:962-1003`, `:752`).
   A Cmd+Z of the turn before the person answers, an undo of single members, and which route (Cmd+Z, Undo all, per-row Undo, by id) was used are not recorded, so the Dark Factory cannot yet measure point 5 on its own data.
9. **The turn preview overstates.** The agent's `dry_run` of a turn undo answers `would_take_back` with the count of the turn's ids whatever the blockers (`ops_brp.rs:3037-3045`), so it is wrong whenever a member would be refused.

## Ideas

Seven lens agents proposed 24 ideas; duplicates were merged to 17, a critic re-read the code for each, and two searchers looked for prior art in engines and editors and in agentic tools and MCP servers.
Six survive.
Scores are 1–5 (Cost 5 = cheapest); Novelty is the lower of the two prior-art searches; the sum ranks, and Evidence breaks ties.
Every claim about the Dark Factory's code is read at `63ab4f724a`, not run.
**Checkpoint D (owner):** all six recommended; no annotations.

|#|Idea|Evidence|Novelty|Vision fit|Leverage|Cost|Sum|
|---|---|---|---|---|---|---|---|
|I1|Turn stamp on every oplog line; real-time Cmd+Z|3|3|5|4|3|18|
|I2|One atomic undo of a set of ids|4|2|4|4|2|16|
|I3|Open the turn in history and card|3|3|4|3|2|15|
|I4|Standing: what the person took back|2|2|5|2|4|15|
|I5|Footprint derived from the recorded line|3|3|4|3|1|14|
|I6|`undo_ask`: the agent asks before taking a person's edit|2|4|4|2|2|14|

Order of work: I1, then I2 (after a write-less commit), then I5; I3's display after I1 and its step undo after I2 and I5; I4 at any time, cheapest after I1; I6 after I2 and I5.

### I1. Stamp the turn on every oplog line, keep Cmd+Z in real-time order, delete the reorder

**Recommended (owner, 2026-11-28).** Owner's annotation: none.

**Problem.** Departures 1, 2, 3 and 8: the stack learns of a turn only at hand-back, `group_turn` then lifts the turn above the person's interleaved edit, and that reorder is what refuses and orphans the turn's oldest members.

**Mechanism and source.** The boundary is the actor's intent, carried by each operation as it is written: Edwards' transactions, Sun's compound operation id, Cordon's delegated-task unit, and the caller-owned scopes every engine ships (Roblox `ChangeHistoryService`, Unreal `FScopedTransaction`, Houdini's undo group, tldraw's marks).

**Sketch.**

- `Entry` (`ops.rs:117-170`) gains a `turn` id; it is minted in one place that both the turn ledger and the undo stack read, because `TurnLedger::turn_begins` returns early when the ledger is not collecting (`turn_ledger.rs:413-415`).
- Agent entries keep their real-time place on the stack; consecutive entries of one turn form a group, and a person's edit inside the turn splits it into runs.
- `group_turn`'s drain and reorder (`editor.rs:422-445`) is deleted.
- The stamp is the only source of "which lines are the turn": `blueprint_present` refuses an `operation_ids` member that lacks the turn's stamp, and the ids stay as the card's list.
- Each undo line records its route (Cmd+Z, Undo all, per-row Undo, by id, agent), so "which turns did a person undo, and how" is a query over the oplog; this absorbs the raw idea of a ledger verdict per undo, and the ledger keeps its `Hands` distinction.
- One rule to write down where E-071 states "Cmd+Z and Undo all take back the same amount": with a turn split by a person's edit, Cmd+Z takes one run and Undo all takes the whole turn.

**Why new.** Grouping by a caller-opened boundary is standard (Unity `CollapseUndoOperations`, Roblox, Unreal, ue-mcp's `begin_transaction`).
nsgo-dev/game makes a kept turn one history command tagged as the agent's, but avoids interleaving by holding the turn in memory until Keep (reported).
Not found: a turn id on each persistent log line as it is written, with the person's history left in real-time order.

Prior art: [nsgo-dev/game #1011](https://github.com/nsgo-dev/game/issues/1011), [Roblox ChangeHistoryService](https://create.roblox.com/docs/reference/engine/classes/ChangeHistoryService), [Unity CollapseUndoOperations](https://docs.unity.com/en-us/engine/6000.6/script-reference/unityeditor/undo/collapseundooperations), [ue-mcp checkpoints](https://github.com/db-lyon/ue-mcp/blob/main/docs/checkpoints.md).

**Test.** With real-time order a1, h1 (the person's), a2, a3 and a hand-back of a1–a3: Cmd+Z takes a2 and a3 together, then h1, then a1, and refuses nothing; every turn line carries one stamp; a hand-back citing an unstamped id is refused; the oplog query by route returns each undo.

**Weakest point.** It fixes partiality, not actor scope: real-time order is the global stack human-peer studies rated lowest, so it does not settle the scope question below.

**Critic.** Keep: the reorder is the root cause of the orphaned member, and the stamp is the only idea that makes the boundary visible during the turn; the Nuss citation the lens gave for real-time order was misapplied.

### I2. One atomic undo of a set of ids, used by every walker

**Recommended (owner, 2026-11-28).** Owner's annotation: none.

**Problem.** Departures 3 and 9: a group undo is partial in four walkers with two rules, and the agent's turn `dry_run` reports the full count whatever the blockers.

**Mechanism and source.** Azurite's three outcomes on a conflict (undo only the free changes, undo the blockers too, or cancel) halved backtracking time, 386.3 s against 768.8 s (n=12).
DistEdit's authors first wanted all-or-nothing and later shipped partial undo; the Claude Code rewind report asks for atomic, announced reverts (reported); Atomix and Cordon show the same unit for agents in harnesses with no person.

**Sketch.**

- One operation, "undo exactly these ids": it judges each member on the map left after the newer members are undone, returns a verdict table (id, phrase, verdict, blocker), and commits all of them in one write or none.
- Azurite's outcomes are three inputs to that one operation (the free ids, the free ids plus their blockers, or nothing), not modes.
- Cmd+Z on a group, Undo all (`present.rs:929-961`), the agent's `turn: true` undo (`ops_brp.rs:3071-3085`) and `jump` (`editor.rs:13866-13925`) all call it; the four walkers are deleted.
- The card's button names the plan when a member is blocked ("Undo 4 of 6; 2 stay because …"), and the agent's `dry_run` returns the same table.
- The stack guard `rows_refusal` (`ops_brp.rs:3275-3307`), today run only on the agent's single-line undo, runs inside the planner.
- Undo all forgets the undone lines the way the agent's turn undo does (`forget_line`), so Cmd+Z after it does not replay the turn member by member [INFERENCE, not run].
- Prerequisite, a commit that does not write: each operation's `commit` saves the file itself (`ops.rs:1778`), so judging member k on the post-undo map needs either a write-less commit or the dispatcher doing the save.

**Why new.** Privatrak and paper-lite ship a verdict per change but skip and report the rest, which is partial (reported); ue-mcp refuses a batch whole before it runs; godot-mcp's pending rollback is atomic.
Not found: one atomic planner shared by the person's keys and the agent's tools, with the three outcomes as inputs.

Prior art: [Privatrak](https://dev.to/quentin_wendegass/we-gave-our-mcp-server-an-undo-button-2mah), [paper-lite #56](https://github.com/rocketonthemoon/paper-lite/pull/56), [ue-mcp #1520](https://github.com/db-lyon/ue-mcp/pull/1520), [godot-mcp undo tools](https://github.com/tomyud1/godot-mcp/blob/main/mcp-server/src/tools/undo-tools.ts).

**Test.** A property test over generated interleavings of person and agent operations: every undo of a set ends with all of it undone, or refused with the blueprint byte-identical, and `dry_run`'s table equals what the real undo then does.

**Weakest point.** The write-less commit touches every operation's `commit`; without it the planner can judge only the first guard and must say it is conservative.

**Critic.** Keep, as the core: the raw ideas' `best_effort` and `all_or_nothing` modes became one operation with three inputs, the ghost preview's table and label and the replay oracle (as this test) were folded in, and the write-less commit is the cost.

### I3. Open the turn in the history panel and the hand-back card

**Recommended (owner, 2026-11-28).** Owner's annotation: none.

**Problem.** Departure 6: a grouped turn is one history row, "N changes" (`editor.rs:1257`), the card lists one bullet per operation (`present.rs:138-145`), and a person cannot see where their own edits fell inside the turn.

**Mechanism and source.** Hierarchical history: Myers & Kosbie's levels, Chimera's panels, Heer's history on 20,192 actions, Chronicle; with the plan step as the middle level, as Magentic-UI and LAVE use for review.
Aquamarine's participants' main request was grouping.

**Sketch.**

- Stage 1, display only, from I1's stamp: the history row is titled with the hand-back's summary and opens to plan steps (from the turn's last `plan_set`; a turn with no plan is one step) and their operations, with the person's own edits during the turn shown in place as "mine, during turn".
- Step status is computed from the log and never written back to `plan.yaml`.
- Stage 2, after I2 and I5: "Undo step" calls I2 with the step's ids, and a jump into the turn shows I2's table before it runs, because `jump` undoes every entry above the target, the person's included.

**Why new.** Turn-level and per-change views ship (nsgo-dev/game's card, VS Code per change, Windsurf's revert to step, Cline per tool use, Replit milestones).
Not found: the person's interleaved edits shown inside the agent's turn.

Prior art: [nsgo-dev/game #1219](https://github.com/nsgo-dev/game/pull/1219), [VS Code review](https://code.visualstudio.com/docs/agents/run/review-code-edits), [Windsurf Cascade](https://docs.devin.ai/desktop/cascade.md), [Replit checkpoints](https://docs.replit.com/features/version-control/checkpoints-and-rollbacks.md).

**Test.** After a turn with two plan steps and one interleaved person edit, the panel shows one turn row, two step rows and the person's edit marked, with counts equal to the oplog's; in stage 2, undoing step 1 takes exactly its ids or shows the blocker table.

**Weakest point.** Plan steps are optional and agent-written, so the middle level is only as good as the agent's plan.

**Critic.** Keep, in two stages: the display needs only I1's stamp, while step undo waits for I2 and I5; a status write-back to `plan.yaml` was cut as a second source of truth.

### I4. Standing: the agent sees which of its changes a person took back

**Recommended (owner, 2026-11-28).** Owner's annotation: none.

**Problem.** Departure 7: after a person's Cmd+Z the agent sees only a changed `undo_next`, and a later `blueprint_present` still lists the undone ids, because the card's steps are each cited id's logged result (`ops_brp.rs:4290-4294`).

**Mechanism and source.** AgentRewind: an agent that resumed without the environment rewound scored 43.9% against 87.8% with it (harness, no person); Cline tells its agent when the person edited its proposed content (code read); Claude Code's post-restore reminder (reported).

**Sketch.**

- One pure function over the oplog's chains, `standing(lines, ids)`, giving each id as in effect or undone, by whom and by which route (I1).
- `blueprint_state` reports it for the open turn's and the last presented turn's ids; `blueprint_present` leaves undone ids off the card and says so in its answer.
- No per-session cursor, which would not survive an editor restart or several MCP servers, and no fence against re-sending, for which no source shows a need.

**Why new.** nsgo-dev/game's read-only `turn_status` reports reverted changes to the agent (reported); here the same fact comes from the log both actors already share.

Prior art: [nsgo-dev/game #1219](https://github.com/nsgo-dev/game/pull/1219), [cline responses.ts](https://github.com/cline/cline/blob/d92f9393acec3f7f6d8b2bdf59f2c7e1d23ccb87/apps/vscode/src/core/prompts/responses.ts).

**Test.** A person undoes one of three agent operations; `blueprint_state` reports it undone by a person through Cmd+Z, and presenting all three ids shows two and names the third.

**Weakest point.** The evidence that telling the agent changes its behaviour is from harnesses and one reported product.

**Critic.** Keep, trimmed: one pure function instead of the same fact in three places with a per-session cursor, and no re-send fence.

### I5. Footprint derived from the recorded line

**Recommended (owner, 2026-11-28).** Owner's annotation: none.

**Problem.** Departure 4: the first guard refuses on any newer change anywhere on the map and names only the newest blocker, and `layout_accept`'s second-guard state is counts only (`ops.rs:1830-1845`), so any placement added or removed by anyone refuses the undo of a keep.

**Mechanism and source.** DistEdit's map-wide rule was "too restrictive in practice" (Prakash & Knister 1994); Causality records each command's targets so conflicts after a history edit are computable; Atomix's too-narrow scopes committed 66 of 200 invariant violations (harness); Aquamarine abandoned exact pixel-level detection for false positives; Azurite added an operation to its history in 3.93 ms at 10,000 operations.

**Sketch.**

- A required method on every operation, `footprint(line) -> Footprint`, with no default, as `writes()` and `shows()` already are; it is derived from the recorded line's `inverse` and `after`, so old logs need no migration.
- `Footprint::Map` is a declared value for operations that really touch everything; lines that change no map data, `plan_set` today, declare an empty footprint.
- The first guard becomes footprint overlap and names every blocker; the second guard's `state_of` (`ops.rs:9136-9160`) becomes this same declaration rather than a second one.
- `layout_accept`'s line records the row ids it laid and consumed instead of counts.
- Entries that live only on the stack (`RemovedMany`, `RemoveAt`, the unstamps) keep `rows_refusal`.
- A test lists every operation with its footprint kind, so a new operation cannot land without one.

**Why new.** paper-lite compares field values (reported), ue-mcp refuses a file edited outside, s&box declares the objects an undo captures.
Not found: declared footprints used to refuse an undo and name every blocker.

Prior art: [paper-lite #56](https://github.com/rocketonthemoon/paper-lite/pull/56), [ue-mcp checkpoints](https://github.com/db-lyon/ue-mcp/blob/main/docs/checkpoints.md), [s&box undo](https://sbox.game/dev/doc/editor/undo-system).

**Test.** A person's nudge of a lamp far from an agent's fence no longer blocks undoing the fence; nudging a piece the fence touched still does and names the nudge; an unlisted `plan_set` blocks nothing; false refusals on recorded interleavings fall.

**Weakest point.** An under-declared footprint silently allows an overwrite, and the method lands on about 65 operations.

**Critic.** Keep, reframed: "unknown means whole map" and a migration default were cut as second paths, the declaration was unified with the existing second guard, and the incremental index was deferred until a slowness is measured.

### I6. `undo_ask`: the agent asks before taking a person's edit

**Recommended (owner, 2026-11-28).** Owner's annotation: none.

**Problem.** The agent's undo by id may take a person's line (`ops.rs:9033-9040`), and `blueprint_run_command` with `edit.undo` presses the person's Cmd+Z (`ops_brp.rs:3636`) [INFERENCE, not run], a second door past #530's fence.

**Mechanism and source.** Tanagra's rule that the system may not override the person's decisions; Azurite asks the undoer; 40–45% of Nuss's participants expected a confirmation before undoing a feature another user's change depended on; Abowd & Dix: ask when the actions do not commute.
The Dark Factory already has the pattern in `note_ask`.

**Sketch.**

- An actor rule: the agent may not undo a person's line without an answered ask.
- `undo_ask` puts a row in the Agent block, copied from `note_ask`, showing I2's table; the answer line declares an empty footprint (I5).
- `edit.undo` from the agent goes through the same rule.
- Measure first on the bench how often an agent tries it.

**Why new.** Shipped tools refuse (the Dark Factory today), report a partial undo (paper-lite) or undo blindly (unity-mcp's `Undo.PerformUndo()`); none asks the person.

Prior art: [paper-lite #56](https://github.com/rocketonthemoon/paper-lite/pull/56), [unity-mcp ManageEditor.cs](https://github.com/CoplayDev/unity-mcp/blob/19b66ecef4ac3a9be22a7a62ea21accb975c39e7/MCPForUnity/Editor/Tools/ManageEditor.cs), [MCP schema](https://modelcontextprotocol.io/specification/2025-06-18/schema).

**Test.** The agent's undo by id of a person's placement waits for an ask and changes nothing; yes undoes it, no leaves it; `edit.undo` from the agent over a person's newest entry is fenced the same way.

**Weakest point.** No source shows agents doing this, so its frequency is unknown.

**Critic.** Keep, after I2 and I5, with the `edit.undo` door closed too; measure the frequency on the bench first.

## Dropped ideas

|Idea|Why dropped|
|---|---|
|Refuse by consequence: run the map's own checks on the planned undo|Unsound as written: the second guard exists only for operations that declare a state, so dropping the map-wide guard leaves most operations with none.|
|Net-effect turn digest (first-before, last-after per entity)|A net inverse is a second undo semantics beside the per-line chain; read the ledger's operations per turn first.|
|Regional Cmd+Z|The measured sources disagree for this setting (Seifried against Rasch), and it needs a setting choosing between two undo behaviours plus a second chord.|
|"Another layout": regenerate around touched rows|A feature above undo grouping; Unreal's PCG ships manual edits that survive regeneration.|
|Undo settles against the running game|The generic "was this write applied" problem of every write; `reload_files` already reports the game's verdict.|
|Pending-review marks on the map|A review feature whose undo kernel is I2 and I5; recording Keep as an oplog line would duplicate the ledger.|
|Approval guard on what Undo cannot give back|Approval gating, not undo grouping, and its dial is three modes.|
|Ghost overlay of an undo on the map|A second rendering of I2's table; the table and the button label are kept in I2.|
|Replay oracle as a runtime receipt|A second implementation of undo running beside the real one; kept as I2's property test.|
|Keep carries a reproducible recipe|`rules_hash` is only ever written as `None` (`ops.rs:8849`) and the hash would miss the library; the laid and consumed row ids moved into I5.|
|Turn ledger verdict per undo|Merged into I1: with a stamp and a route on each undo line it is a query, and a second store of the same fact is not needed.|

## Guidance this contradicts

Lines are at `bevy_dark_factory` main `63ab4f724a` and `dark-incorporated.github.io` main `1588ac41b7`, found by searching every family repository for undo claims.
Nothing below was edited by this run.

|Where|What it says|What contradicts it|Action it needs|
|---|---|---|---|
|`bevy_dark_factory/docs/guide/agents.md:328`|"Without one, it takes back the newest change still in effect."|The code since #530: an agent's untargeted undo takes back the agent's own newest change, never a person's (`ops.rs:9033-9040`).|Stale; fix the sentence.|
|`bevy_dark_factory/crates/dark_factory_mcp/src/main.rs:153` and `:2449-2450`, generated into `docs/mcp-tools.md:229`|"omit it to take back the newest change that has not been taken back"|The same #530 behaviour. `docs/mcp-tools.md` is generated from the tool descriptions (`crates/dark_factory_mcp/src/lib.rs:24-25`), so the source must change and the file be regenerated.|Stale; fix the tool description, regenerate.|
|`bevy_dark_factory/docs/PROJECT.md:80` (and the one-sentence summary at `:13`)|"**One undo history.** The agent's change joins yours, and `Cmd+Z` takes back the newest change still in effect, whoever made it."|The code: after a hand-back, `group_turn` puts the agent's turn above a person's interleaved edit, so Cmd+Z takes the turn before the person's newer edit (`editor.rs:422-445`; read, not run). The evidence: global undo was the least preferred scope among human peers (Nuss ≤25%, Seifried 22%), though Rasch found a shared stack best under close collaboration.|The code half is a bug report; the scope half waits for the decision in "Alternatives" below.|
|`bevy_dark_factory/docs/guide/getting-started.md:79` (synced to `dark-incorporated.github.io/src/crates/bevy_dark_factory/guide/getting-started.md:80`)|"each Cmd+Z removes the most recent change, one change at a time, whoever made it."|A grouped agent turn is many changes per Cmd+Z (E-071), and the reorder above means it is not always the most recent.|Fix with the PROJECT.md line; the site copy follows the sync.|
|`bevy_dark_factory/docs/guide/building-maps.md:179` (synced to the site's `building-maps.md:180`)|"Press `Cmd+Z` to take back the last change on the Map, whoever made it."|The reorder above.|As above.|
|`bevy_dark_factory/crates/bevy_dark_factory/src/ops_brp.rs:2822-2823` (comment)|"Cmd+Z takes back the newest change whoever made it, not the newest the person made by hand."|The reorder above.|Fix with the code change.|
|`bevy_dark_factory/README.md:15`, `crates/bevy_dark_factory/README.md:15`, `crates/dark_factory_mcp/README.md:9`, `docs/guide/README.md:8`|"into the same undo history", "in the same undo history", "the same undo history", "a shared undo"|True of the person's Cmd+Z; no longer true of the agent's undo after #530, and in tension with the human-peer evidence.|Wait for the scope decision.|
|`.github/docs/research/2026-11-02-game-editor-best-practices.md:74`|"Check how undo groups work. Ask whether one agent request that touches several things becomes one undo step."|Answered since by E-071 (a presented turn is one `Undo::Group`) and by this document.|None; that file is a record of what was believed and is not rewritten.|

## Alternatives and what would decide them

- **I1, scope of the person's Cmd+Z: global (today), per actor, or regional.**
  Among human peers global undo was the least preferred (Nuss ≤25%, Seifried 22%), but Rasch found a shared stack best under close collaboration (n=32).
  Decided by the Dark Factory's own data once I1 records routes: how often a person's Cmd+Z of an agent change is followed by a redo within a minute, the sign it took what they did not mean.
- **I1, where the turn lives until Keep: live and stamped, or pending.**
  I1 keeps the agent's writes live and stamps them; nsgo-dev/game holds the turn pending and commits one step at Keep (reported).
  Decided by reading nsgo-dev/game's code, and by whether people undo single agent edits before they answer, which I1's routes will show.
- **I2, atomic or partial.**
  I2 is atomic; DistEdit shipped partial because its users preferred it, and Privatrak and paper-lite skip and report.
  Decided by counting, on the bench and in the ledger, how often a turn undo meets a blocker, and which of Azurite's three outcomes people pick when it does.
- **I3, a plan-step middle level or none.**
  Decided by the ledger's operations per turn (`OpenTurn.seen`, `turn_ledger.rs:432`): if most turns are a handful of operations, I3 needs only its turn and operation levels.
- **I4, the agent pulls its standing or is told.**
  I4 is read from `blueprint_state` and applied at `blueprint_present`; the alternative pushes each undo of an agent line into the agent's next answer, as Claude Code's post-restore reminder does (reported).
  Decided on the bench by how often an agent acts on an id a person already undid under each design.
- **I5, how to decide that an undo conflicts: declared footprints, values, or consequences.**
  I5 uses footprints; paper-lite compares values; the dropped consequence idea ran the map's checks.
  Decided by replaying the same recorded interleavings through each test and comparing false refusals with missed overwrites.
- **I6, ask or refuse.**
  The alternative extends #530's fence: the agent's undo by id of a person's line is refused outright.
  Decided on the bench by how often an agent attempts it and, once I6 exists, how often the person answers yes; rare attempts or a rare yes favour the refusal.

## Method and limits

**Discovery** ran in two rounds through home-still's `discover`, `graph` and `recall`.

- Round 1, 15 queries: selective undo collaborative editing; group undo interleaved edits multi-user; undo operational transformation CRDT; human-AI co-editing provenance revert; undo granularity user study; regional undo graphical editor; editable graphical history visualization; non-linear undo history branching; undo command pattern transaction grouping; mixed-initiative level design tool; AI agent checkpoint rollback code edits; provenance of edits trust human-AI collaboration; multi-user undo game level editor; version control 3D scenes merge; undo in direct manipulation interfaces.
  It returned 296 works.
- Round 2, 11 new queries: rollback LLM agent actions undo; hierarchical command objects undo; undo erase events usability problems; backtracking strategies developers study; workflow history visualization document editing; mesh editing workflow summarization; guidelines human-AI interaction efficient correction; mixed-initiative user interfaces principles; version control LLM agent state; transactional compensation multi-step agent; undo multi-user CAD expectations.
  Plus 10 DOI lookups and the citation graph of six seed papers (Azurite, Berlage 1994, Prakash & Knister 1994, Causality, Sun 2000, Rasch 2024), in both directions.
  It returned 496 new works.
- Providers that answered: arXiv, OpenAlex (live and the local corpus), Europe PMC, Crossref.
  CORE refused every call for want of an API key.
  Semantic Scholar was rate-limited and then tripped its circuit breaker for most of round 2.
- `graph` through the local OpenAlex corpus failed for four of six seeds ("the local OpenAlex corpus has no work with DOI …"); Semantic Scholar answered for citations, but its reference lookup failed for five of six seeds ("Failed to parse Semantic Scholar references: error decoding response body").
- `recall` over the academic, abstracts, web and syntheses stores found nothing on point beyond Ousterhout; the syntheses store was empty.

**Screening.** Of 792 works, 60 were kept (the cap of the `--exhaustive` tier), and the owner kept all 60 at the checkpoint.
**Stop reason: the cap, not saturation.** Round 2 still produced on-topic works the cap left out.

**Acquisition and reading.**

- 51 of 60 papers were acquired: 20 through home-still's `acquire` and 31 through Anna's Archive SciDB, ingested into home-still.
- 50 were read in full by reader agents, each writing a note with the claim, the evidence, its strength and the line numbers of quotations.
- One acquired file was the wrong paper (see the Sources table).
- 43 web pages were captured into home-still and read: engine and editor documentation, agentic tool documentation, issues, forum threads, vendor posts, two patents, and the Nuss 2016 thesis.
- 7 source trees were read at pinned commits (Blender, Fyrox, Godot, Yjs, aider, `bevy_editor_prototypes`, tldraw).
- One Reddit thread was read but could not be captured, so it is cited as reported only.

**Ideas.** Seven lens agents proposed 24 ideas from the synthesis and the code facts; they were merged to 17, then a critic and two prior-art searchers (engines and editors; agentic tools and MCP servers) reviewed each one before scoring.
The critic re-read the code for each idea and corrected two findings of this document: the group undo's refusal is named in the status line, and the ledger already labels a person's undo after a Keep.
The prior-art searchers captured 24 more pages into home-still, listed under Sources; nsgo-dev/game, paper-lite and Privatrak, the closest, were read from their issue, PR or post text only, not their code.

**Limits.**

- No source studies a person and an AI agent editing the same world; every conclusion about the Dark Factory is transferred from human-peer, single-user or person-free agent studies.
- The Dark Factory's behaviour was read from source at `63ab4f724a`, not run; every claim about what a group undo does at run time is an inference from the code.
- The cap stopped discovery while round 2 was still finding relevant work.
  The ten papers not obtained or not usable include three that bear directly on RQ2: *Detecting local undo conflicts in multi-user CAD* (2016, the wrong file), *Using Task Models for Cascading Selective Undo* (2006) and a 2026 selective undo algorithm for dependency-constrained histories; and two on version control of 3D scenes, VRGit (2023) and SceneGit (2019).
- Forum, issue, vendor-blog and patent sources are labelled reported throughout, and the claim that reverts silently take a person's edits rests mostly on them.
