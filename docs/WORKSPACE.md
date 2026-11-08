# The workspace: where Dark Inc. repositories live on a machine

One layout on every machine, so a person, a loop and an agent all find a repository in the same place and never work in each other's copy.

## Layout

- Every machine has `~/dark-incorporated/`.
- Each repository is cloned once: `git clone git@github.com:dark-incorporated/<repo>.git ~/dark-incorporated/<repo>`, on `main`, tracking `origin/main`.
- [`tools/workspace.sh`](../tools/workspace.sh) keeps it so:
  - `tools/workspace.sh sync` clones every repository that is missing and fetches the rest. It changes nothing else.
  - `tools/workspace.sh audit` prints one row per family clone and worktree on the machine (path, remote, branch, ahead, behind, dirty files, stashes, worktrees, last commit, size) and a `DUPLICATE` line for every repository that is there more than once.

## Who owns the clone

- **If a loop runs for that repository on that machine, the loop owns the clone.** Never edit it, and never `reset`, `checkout` or `clean` it: a pass may be mid-edit, and its uncommitted work would be lost without a trace. To work in a loop's repository, stop the loop at a pass boundary first (`WIGGUM_REPO=<clone> wiggum.sh guard`, then `stop`).
- **Without a loop, the clone still stays on a clean `main`.** All work happens in worktrees.

## Worktrees

Create one per task:

```sh
git -C ~/dark-incorporated/<repo> fetch -q
git -C ~/dark-incorporated/<repo> worktree add -b <branch> /tmp/dark-incorporated/<repo>-<task> origin/main
```

- `<task>` is kebab-case: `/tmp/dark-incorporated/bevy_gooey-toast-actions`.
- A comparison baseline is detached: `git -C ~/dark-incorporated/<repo> worktree add --detach /tmp/dark-incorporated/<repo>-base-<shortsha> <sha>`.
- Builds use the shared `CARGO_TARGET_DIR`, never a target directory inside the worktree.

## Cleanup

When the work is merged and pushed:

```sh
git -C ~/dark-incorporated/<repo> worktree remove /tmp/dark-incorporated/<repo>-<task>
git -C ~/dark-incorporated/<repo> branch -d <branch>
```

After a reboot, run `git -C ~/dark-incorporated/<repo> worktree prune` so the clone forgets worktrees that are gone.

## RAM-backed /tmp

On a machine where `/tmp` is tmpfs (`findmnt -no FSTYPE /tmp` prints `tmpfs`), a reboot erases every worktree. Push the branch before ending a session.

## No other copies

No `_base`, `_ref`, `_wN`, `-docs` or `-work` clones, and no second clone for a loop. A second loop on one repository runs on another machine, not in a second clone on this one.
