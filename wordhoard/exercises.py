"""Exercise logic: what to ask, and how to grade what comes back.

Vertical slice step 4, the typing exercise. Prompt in English, learner types the
target language.

This module holds no database access and no scheduling. It takes a content row
and a typed string and returns a judgement. Step 5 is the wiring that reads the
due queue, calls in here, and feeds the resulting rating to the scheduler.
Keeping the judgement pure makes it testable without a database, which matters
more than usual on this project: the person building it cannot read German, so
the grader's behaviour has to be demonstrable case by case.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Determiners the content actually uses. Measured against the live database on
# 2026-08-26: of 74 drillable answers, 42 begin with one of these, and the
# remaining four multi-word answers are phrases ('ich komme aus Berlin',
# 'da drüben') rather than determined nouns.
#
# This is why "the answer contains a space" is NOT the test for a determined
# noun, which was the obvious first implementation and is wrong on four items.
# The test is: the item is a noun, and its first token is one of these.
DETERMINERS = frozenset({"der", "die", "das", "mein", "meine"})

# Which genders each determiner is consistent with. This exists to stop the
# grader telling a learner something false.
#
# Family nouns are drilled with a possessive ('mein Bruder'), but 'der Bruder'
# is perfectly correct German and demonstrates exactly the knowledge being
# tested, namely that Bruder is masculine. Grading it as "wrong gender" would be
# a lie, and a lie about the one thing this exercise is for. So a determiner
# that disagrees with the stored gender is an error, while a determiner that
# agrees but is not the drilled form is an accepted variant with a note.
#
# 'mein' covers masculine and neuter because the possessive does not distinguish
# them in the nominative, which is a fact about German rather than a shortcut.
DETERMINER_GENDERS = {
    "der": frozenset({"m"}),
    "die": frozenset({"f"}),
    "das": frozenset({"n"}),
    "mein": frozenset({"m", "n"}),
    "meine": frozenset({"f"}),
}

# German transliterations accepted when the umlaut or eszett cannot be typed.
# These are the standard substitutions, universally understood, and they are the
# ones the source mindmap itself used ('die Haeuser' for 'die Häuser').
#
# Note what this deliberately does NOT accept. Folding is applied to both sides,
# so 'Baeckerei' matches 'Bäckerei', while 'Backerei' (the umlaut simply
# dropped) does not match anything and is graded wrong. That is the right line:
# a learner without a German keyboard is accommodated, a learner who has
# forgotten the umlaut exists is not.
#
# Affects 10 of the 74 drillable answers, measured 2026-08-26.
TRANSLITERATIONS = {
    "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
    "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
}

# Collapses runs of whitespace, so a double space between determiner and noun is
# not an error. Nobody is learning about spaces.
WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Grade:
    """The full judgement on one typed answer.

    Deliberately richer than the single FSRS rating it carries. The scheduler
    only ever sees `rating`, but the exercise needs the detail to tell the
    learner *what* went wrong, and 'right word, wrong gender' is the specific
    feedback this project exists to give.
    """

    rating: int                      # 1 again, 2 hard, 3 good. See RATINGS below.
    correct: bool                    # fully correct, nothing to correct
    word_correct: bool               # the noun or verb itself was right
    determiner_correct: bool | None  # None when the answer takes no determiner
    determiner_variant: bool         # correct gender, but not the drilled form
    capitalisation_correct: bool
    used_transliteration: bool       # matched via 'ue' for 'ü' and friends
    expected: str
    given: str
    feedback: str


def normalise(text: str) -> str:
    """Trim and collapse whitespace. Case and diacritics are left alone.

    Also normalises Unicode to NFC, so that an 'ä' typed as a combining
    diaeresis compares equal to one typed as a single code point. Different
    keyboards and paste sources produce different encodings of the same letter,
    and marking that wrong would be indefensible.
    """
    return WHITESPACE.sub(" ", unicodedata.normalize("NFC", text).strip())


def fold(text: str) -> str:
    """Apply the accepted transliterations, for comparison only.

    Never used for display. The learner is always shown the properly spelled
    form, so that accommodating a keyboard does not teach a wrong spelling.
    """
    for character, replacement in TRANSLITERATIONS.items():
        text = text.replace(character, replacement)
    return text


def expected_answer(item: dict) -> str:
    """The string the learner is expected to type.

    This is the one place the answer_form fallback is implemented, as the schema
    comment requires. answer_form holds what a noun is actually learned as
    ('das Haus', 'mein Bruder') and is NULL for verbs, adjectives and adverbs,
    where the bare lemma already is the answer. Restating this fallback at each
    call site is how the two would eventually disagree.
    """
    answer_form = item.get("answer_form")
    return normalise(answer_form) if answer_form else normalise(item["lemma"])


def split_determiner(text: str, is_noun: bool) -> tuple[str | None, str]:
    """Split a leading determiner off an answer, if there is one to split.

    Returns (determiner, rest). The determiner is None for anything that is not
    a determined noun, which covers verbs, adjectives, and the handful of
    phrases whose first word merely looks like it could be a determiner.
    """
    if not is_noun:
        return None, text

    parts = text.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() in DETERMINERS:
        return parts[0], parts[1]
    return None, text


def grade(item: dict, given: str) -> Grade:
    """Judge one typed answer against one content item.

    The grading rules, all three decided by the user rather than by me:

    1. The determiner and the noun are graded SEPARATELY, so a correct noun with
       the wrong article reports "right word, wrong gender" instead of a flat
       wrong. It is the better learning signal, and it is the reason answer_form
       exists at all.
    2. Capitalisation of the NOUN is enforced. German nouns are capitalised and
       the point is to learn that, not to be excused from it.
    3. Capitalisation of the DETERMINER is not graded. 'Das Haus' at the start of
       a sentence is ordinary German, and marking it wrong would be teaching a
       rule that does not exist.
    """
    expected = expected_answer(item)
    given_normalised = normalise(given)
    is_noun = item.get("part_of_speech") == "noun"

    expected_determiner, expected_word = split_determiner(expected, is_noun)
    given_determiner, given_word = split_determiner(given_normalised, is_noun)

    # The word itself, tested in three widening circles: exact, then
    # transliterated, then case-insensitive. The order matters, because it is
    # what distinguishes "right but mis-capitalised" from "wrong".
    word_exact = given_word == expected_word
    word_transliterated = fold(given_word) == fold(expected_word)
    word_case_insensitive = fold(given_word).lower() == fold(expected_word).lower()

    word_correct = word_case_insensitive
    used_transliteration = word_transliterated and not word_exact

    # Capitalisation is graded on NOUNS ONLY. That is exactly the rule the user
    # chose: German nouns take a capital and the point is to learn it. It is not
    # a general rule about matching case, and applying it to verbs would fail
    # 'Gehen' for a capital letter that breaks no German rule the learner is
    # being taught. For non-nouns a case-insensitive match is fully correct.
    if is_noun:
        capitalisation_correct = word_exact or word_transliterated
    else:
        capitalisation_correct = True

    # The determiner, compared case-insensitively per rule 3. None when the
    # expected answer takes no determiner, so that "no determiner required" and
    # "determiner wrong" stay distinguishable in the result.
    determiner_correct: bool | None = None
    determiner_variant = False
    if expected_determiner is not None:
        if given_determiner is None:
            determiner_correct = False
        elif given_determiner.lower() == expected_determiner.lower():
            determiner_correct = True
        else:
            # A different determiner that nonetheless agrees with the stored
            # gender: 'der Bruder' against a drilled 'mein Bruder'. The gender
            # knowledge is demonstrated, which is what the exercise is testing,
            # so this counts as correct and earns a note rather than a mark.
            gender = item.get("gender")
            agrees = gender in DETERMINER_GENDERS.get(given_determiner.lower(), frozenset())
            determiner_correct = bool(agrees)
            determiner_variant = bool(agrees)

    correct = word_correct and capitalisation_correct and determiner_correct is not False

    rating, feedback = _rate(
        expected=expected,
        expected_word=expected_word,
        correct=correct,
        word_correct=word_correct,
        determiner_correct=determiner_correct,
        capitalisation_correct=capitalisation_correct,
        given_determiner=given_determiner,
        used_transliteration=used_transliteration,
        determiner_variant=determiner_variant,
    )

    return Grade(
        rating=rating,
        correct=correct,
        word_correct=word_correct,
        determiner_correct=determiner_correct,
        determiner_variant=determiner_variant,
        capitalisation_correct=capitalisation_correct,
        used_transliteration=used_transliteration,
        expected=expected,
        given=given_normalised,
        feedback=feedback,
    )


def _rate(
    *,
    expected: str,
    expected_word: str,
    correct: bool,
    word_correct: bool,
    determiner_correct: bool | None,
    capitalisation_correct: bool,
    given_determiner: str | None,
    used_transliteration: bool,
    determiner_variant: bool,
) -> tuple[int, str]:
    """Turn a judgement into an FSRS rating and a line of feedback.

    FSRS defines four ratings: 1 again, 2 hard, 3 good, 4 easy. This grader
    produces only 1, 2 and 3, and never 4.

    Easy is deliberately unreachable, because a typing exercise cannot observe
    effort. A correct answer typed slowly and a correct answer typed instantly
    look identical to this function, and guessing between them would feed the
    scheduler a number it did not earn. The consequence is real and worth
    stating: intervals for genuinely easy items will grow more slowly than a
    learner pressing Easy in Anki would see. If that becomes annoying, the fix
    is an explicit "that was easy" control in the interface, not an inference
    here. Logged in docs/TODO.md.

    Item 4a-i, twice deferred, is settled here by measurement rather than
    taste. Against a mature item (stability 90 days, retention 0.9, fuzzing off)
    the three ratings do this:

        Again   stability 90 -> 3.6      back in 10 minutes
        Hard    stability 90 -> 172.7    back in 173 days
        Good    stability 90 -> 227.5    back in 227 days

    Hard is not a middle course. It is a near-miss of Good, and an item rated
    Hard is gone for the better part of a year. So rating a wrong gender as Hard
    would mean the gender error is told to the learner and then never drilled
    again, which defeats the entire reason answer_form exists.

    Hence the split below, which grades generously in what it SAYS and honestly
    in what it FEEDS the scheduler:

    * Wrong or missing determiner is Again. The item being scheduled is
      'das Haus', not 'Haus', and the learner did not produce it. Gender is
      per-word knowledge and Again is the only rating that brings it back soon.
    * Capitalisation alone, with the word and gender both right, is Hard. That
      is a deliberate exception. Noun capitalisation is a single systematic rule
      rather than 42 separate facts, so a missed shift key says nothing about
      whether this particular word is known, and destroying 96% of an item's
      hard-won stability over it would make the tool punishing to use.
    """
    if correct:
        # Notes, not corrections. Both cases below are fully correct answers
        # that are nonetheless worth a word, so the phrasing must not read as a
        # telling-off. Note also that 'ß' is an eszett rather than an umlaut, so
        # the wording says spelling generally rather than naming the wrong mark.
        notes = []
        if used_transliteration:
            notes.append(f"the full spelling is {expected}")
        if determiner_variant:
            notes.append(
                f"{given_determiner} {expected_word} is right too, "
                f"though this one is drilled as {expected}"
            )
        if notes:
            return 3, "Correct. " + _sentence("; ".join(notes))
        return 3, "Correct."

    if not word_correct:
        return 1, f"The answer was {expected}."

    # From here the word itself was right, so the failure is partial. The
    # determiner branch is Again and the capitalisation branch is Hard, for the
    # measured reasons in the docstring above.
    if determiner_correct is False:
        if given_determiner is None:
            problem = f"right word, but it needs its article: {expected}"
        else:
            problem = (
                f"right word, wrong gender: {expected}, not "
                f"{given_determiner} {expected_word}"
            )
        if not capitalisation_correct:
            problem += f"; German nouns also take a capital: {expected_word}"
        return 1, _sentence(problem)

    return 2, "Nearly. " + _sentence(
        f"German nouns take a capital: {expected}"
    )


def _sentence(text: str) -> str:
    """Capitalise the first letter and add a full stop.

    Deliberately not str.capitalize(), which lowercases everything after the
    first character. On German feedback that would turn 'der Bruder is right'
    into 'Der bruder is right', which is exactly the error the grader is
    supposed to be teaching against.
    """
    return text[:1].upper() + text[1:] + "."
