---
name: local-only-git-no-remote
description: The repo is local only with no origin, so the Wrap Up push step does not apply
metadata:
  type: project
---

The git repository was initialised locally on 2026-08-23 with no remote, and
none is planned for now.

**Why:** Confirmed by the user when the repository was created. This is a
personal tool on one machine and there is nothing to push to.

**How to apply:** Stop the Wrap Up sequence after step 4 (commit, which still
requires explicit confirmation of the message). Skip step 5 (push) and say it
was skipped because there is no remote, rather than trying to create or guess
one.
