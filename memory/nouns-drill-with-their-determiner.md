---
name: nouns-drill-with-their-determiner
description: Nouns are always drilled with their article, and family members with their possessive; never accept the bare noun
metadata:
  type: project
---

The expected answer for a German noun is `das Haus`, never `Haus`. For family
members it is the possessive form the learner studied: `mein Bruder`, `meine
Schwester`, not `der Bruder`. This is held in `lexical_items.answer_form`, which
is separate from `lemma` (the bare dictionary form that joins and frequency
lookups key on).

**Why:** Stated by the user on 2026-08-23. It is how people actually learn
German nouns, and gender is the hard part. Accepting a bare noun quietly excuses
the learner from the thing being tested, and the learner would never find out
they had it wrong.

**How to apply:**

- When authoring or importing content, populate `answer_form` for every noun.
  `scripts/draft_german.py` derives it from gender and asserts that no gendered
  noun escapes without a determiner.
- `answer_form` is NULL for verbs, adjectives, adverbs and phrases, where the
  lemma is already the answer. Implement that fallback once, in `wordhoard`.
- The same rule applies to Dutch when it arrives, and matters more there: `de`
  against `het` is the classic stumbling block, and the source Dutch mindmap
  already has three of them wrong. See
  [[learner-cannot-verify-target-language]].
- Do not add derivation-from-gender as a substitute for the column. It handles
  `der Tisch` and cannot express `mein Bruder`.
- **Grade the determiner and the noun separately** (decided 2026-08-23), so a
  wrong article on a correct noun reports "right word, wrong gender" instead
  of a flat wrong. It is the better learning signal.
- **Capitalisation is enforced** (decided 2026-08-23). A lowercase German noun
  is marked wrong. The user chose strictness deliberately: the point is to
  learn it correctly rather than to be let off.
