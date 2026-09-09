---
name: git-remote-and-push
description: The repo pushes to https://github.com/IanTW/Word-Hoard on branch main; the earlier local-only assumption is obsolete
metadata:
  type: project
---

The repository has a remote. `origin` is
`https://github.com/IanTW/Word-Hoard.git` and the branch is `main`, tracking
`origin/main`.

**Why:** The repo was created local-only on 2026-08-23, then the user added a
GitHub remote on 2026-08-24. The first attempt used the wrong URL
(`Word_Hoard` with an underscore rather than `Word-Hoard` with a hyphen), which
was corrected with `git remote set-url` rather than by removing and re-adding.

This file, `MEMORY.md` and `CLAUDE.md` all said the branch was `master` until
2026-09-07, when `git branch -a` was checked and reported `main` tracking
`origin/main`. The three were corrected together. Do not reintroduce `master`
from an older note; verify against `git branch` if in doubt.

**How to apply:** Wrap Up step 6 (push) now applies. Run it after the commit in
step 5 lands. Never force-push. Note this supersedes the earlier standing
instruction to skip the push step, so do not skip it.
