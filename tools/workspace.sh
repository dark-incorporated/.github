#!/usr/bin/env bash
# Dark Inc. workspace tool. One clone per repo per host at ~/dark-incorporated/<repo>.
#
#   tools/workspace.sh audit   list every family clone and worktree on this host, one TSV row each
#   tools/workspace.sh sync    clone each missing org repo into $ROOT, fetch the rest; changes nothing else
#
# Env: ORG (default dark-incorporated), ROOT (default $HOME/$ORG).
# Runs on macOS bash 3.2 and Linux bash. See docs/WORKSPACE.md.
set -u

ORG="${ORG:-dark-incorporated}"
ROOT="${ROOT:-$HOME/$ORG}"
HOST="$(hostname -s 2>/dev/null || hostname)"
# Remotes that count as family clones.
MATCH="$ORG/|bevy-coven/|dark-incorporated/|Ladvien/sanctuary|Ladvien/foundation_vs_slop|Ladvien/godot_sanctuary"

usage() {
    echo "usage: workspace.sh audit|sync" >&2
    exit 64
}

# Every git directory up to depth 3 under $HOME, pruning caches, mounts and build output.
repos() {
    find "$HOME" -maxdepth 4 \
        \( -name Library -o -name target -o -name node_modules -o -name .cache -o -name .cargo -o -name .rustup \
        -o -name .Trash -o -name .local -o -name .npm -o -name mnt -o -name gh-runners -o -name .omp -o -name Dropbox \) -prune \
        -o -name .git -print 2>/dev/null |
        while read -r g; do dirname "$g"; done
}

# Size of a working tree in KiB, leaving out cargo target directories.
size_kb() {
    if du --version >/dev/null 2>&1; then
        du -sk --exclude=target "$1" 2>/dev/null | awk '{print $1}'
    else
        du -sk -I target "$1" 2>/dev/null | awk '{print $1}'
    fi
}

row() {
    local p="$1" remote branch ab ahead behind dirty stashes wts last size
    remote="$(git -C "$p" config --get remote.origin.url 2>/dev/null)" || return 0
    echo "$remote" | grep -Eq "$MATCH" || return 0
    GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=10" git -C "$p" fetch -q 2>/dev/null
    branch="$(git -C "$p" rev-parse --abbrev-ref HEAD 2>/dev/null)"
    ab="$(git -C "$p" rev-list --left-right --count '@{u}...HEAD' 2>/dev/null)"
    if [ -n "$ab" ]; then
        behind="$(echo "$ab" | awk '{print $1}')"
        ahead="$(echo "$ab" | awk '{print $2}')"
    else
        behind="-"
        ahead="-"
    fi
    dirty="$(git -C "$p" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
    stashes="$(git -C "$p" stash list 2>/dev/null | wc -l | tr -d ' ')"
    wts="$(git -C "$p" worktree list --porcelain 2>/dev/null | grep -c '^worktree ')"
    last="$(git -C "$p" log -1 --format=%cI 2>/dev/null)"
    size="$(size_kb "$p")"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$HOST" "$p" "$remote" "$branch" "$ahead" "$behind" "$dirty" "$stashes" "$wts" "$last" "$size"
}

audit() {
    local out p wt
    out="$(mktemp)"
    printf 'host\tpath\tremote\tbranch\tahead\tbehind\tdirty_files\tstashes\tworktrees\tlast_commit_iso\tsize_kb\n'
    repos | while read -r p; do
        row "$p"
        # Linked worktrees of this clone that live outside $HOME are listed too.
        git -C "$p" worktree list --porcelain 2>/dev/null | sed -n 's/^worktree //p' | while read -r wt; do
            case "$wt" in "$HOME"/*) ;; *) [ -d "$wt" ] && row "$wt" ;; esac
        done
    done | sort -u | tee "$out"
    # A remote cloned more than once on this host (worktrees count as copies too).
    awk -F'\t' '{ r = $3; sub(/\.git$/, "", r); n = split(r, a, /[:\/]/); k = tolower(a[n]); c[k]++; p[k] = p[k] " " $2 }
        END { for (k in c) if (c[k] > 1) printf "DUPLICATE\t%s\t%d\t%s\n", k, c[k], p[k] }' "$out"
    rm -f "$out"
}

sync() {
    local name
    command -v gh >/dev/null || { echo "workspace.sh: gh is not installed" >&2; exit 69; }
    mkdir -p "$ROOT"
    gh repo list "$ORG" --no-archived --limit 200 --json name --jq '.[].name' | while read -r name; do
        if [ -d "$ROOT/$name/.git" ]; then
            git -C "$ROOT/$name" fetch -q && echo "fetched $name"
        else
            git clone -q "git@github.com:$ORG/$name.git" "$ROOT/$name" && echo "cloned  $name"
        fi
    done
}

case "${1:-}" in
    audit) audit ;;
    sync) sync ;;
    *) usage ;;
esac
