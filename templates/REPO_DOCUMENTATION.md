# Documenting {repo}

{repo} follows Dark Incorporated's [documentation guide](https://github.com/dark-incorporated/.github/blob/main/DOCUMENTATION.md) and [style guide](https://github.com/dark-incorporated/.github/blob/main/STYLE.md). They hold every rule; this file holds only what is specific to {repo}, and where it disagrees with them, this file is wrong.

<!-- dark-inc:generated:begin -->
## This repository

| | |
|---|---|
| Part of Dark Inc. | {part} |
| Book chapter | https://dark-incorporated.github.io/crates/{repo}/ |
| Hero media | `{hero}` |
| Captures run on | {capture_host} |
| Art palette subset | `{subset}` |

## Check it locally

```sh
git clone https://github.com/dark-incorporated/.github ../.github   # once, beside this repository
python3 ../.github/tools/readme_check.py --repo .
python3 ../.github/tools/doc_refs_check.py --repo .
python3 ../.github/tools/media_check.py --repo . --stale
python3 ../.github/tools/rename.py --repo . --check
```
<!-- dark-inc:generated:end -->

## Terms used here

None.

## Recorded exceptions

None.
