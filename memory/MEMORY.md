# Memory index

One line per memory file. Read this first, then read the files it points at.

- [Deliberate schema tradeoffs](deliberate-schema-tradeoffs.md): three schema choices that look like bugs and are not; raise, do not refactor.
- [FSRS, not SM-2](fsrs-not-sm2.md): the scheduler; the PyPI package is `fsrs`, and from v6 it supplies the learning steps too, so do not hand-roll them.
- [The review log is append-only](review-log-is-append-only.md): never update or delete it; parameter refitting depends on the raw history.
- [Vertical slice first](vertical-slice-first.md): nothing outside the six steps until step 6 has real usage behind it.
- [No gamification](no-gamification.md): no streaks, XP or mascots; this is why the project exists.
- [Plain-text backup, not the .db file](plain-text-backup-not-db-file.md): the versioned artifact is newline-delimited JSON.
- [Nouns drill with their determiner](nouns-drill-with-their-determiner.md): the answer is `das Haus` and `mein Bruder`, never the bare noun.
- [The learner cannot verify the target language](learner-cannot-verify-target-language.md): the user does not speak German; surface every change and machine-check what can be machine-checked.
- [Git remote and push](git-remote-and-push.md): pushes to IanTW/Word-Hoard on master; the Wrap Up push step applies.
