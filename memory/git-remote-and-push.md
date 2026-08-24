---
name: git-remote-and-push
description: The repo pushes to https://github.com/IanTW/Word-Hoard on branch master; the earlier local-only assumption is obsolete
metadata:
  type: project
---

The repository has a remote. `origin` is
`https://github.com/IanTW/Word-Hoard.git` and the branch is `master`, tracking
`origin/master`.

**Why:** The repo was created local-only on 2026-08-23, then the user added a
GitHub remote on 2026-08-24. The first attempt used the wrong URL
(`Word_Hoard` with an underscore rather than `Word-Hoard` with a hyphen), which
was corrected with `git remote set-url` rather than by removing and re-adding.

**How to apply:** Wrap Up step 5 (push) now applies. Run it after the commit in
step 4 lands. Never force-push. Note this supersedes the earlier standing
instruction to skip the push step, so do not skip it.
