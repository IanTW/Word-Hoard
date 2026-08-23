"""Parse a FreeMind .mm vocabulary mindmap into a reviewable TSV.

Context: the learner kept hand-built mindmaps of German and Dutch vocabulary
while learning. Those are the content source for the first batch of
lexical_items, in preference to a frequency list, because they are already at
the right level, already carry English translations, and already reflect what
this particular person actually studied.

This script deliberately does NOT write to the database. It emits a TSV for a
human review pass first. That is not ceremony: the mindmaps are learner notes
and contain real errors (wrong genders, uncapitalised nouns, typos). Drilling a
wrong gender teaches a wrong gender, and review_log is append-only, so a bad
import is expensive to walk back. Review, then import.

Usage:
    python scripts/parse_mindmap.py path/to/German.mm > german.tsv
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Child nodes in the mindmap are heterogeneous: a word's children may be its
# English translation, a pronunciation hint, an example sentence, a related
# word, or a grammar note. There is no markup distinguishing them, so they are
# classified by shape. Every heuristic below is fallible; anything uncertain is
# passed through to the review column rather than guessed at.

# Pronunciation hints are consistently written in single quotes throughout both
# mindmaps: 'pahk', 'beck-e-rye', 'oo'-bahn. This is the one fully reliable
# signal in the file.
PRONUNCIATION_RE = re.compile(r"^['‘’]")

# Function words used to detect that a line is target-language text rather than
# an English translation. A line like "Der park ist gross" is an example
# sentence; "nice to meet you" is a translation. Both have spaces, so length
# alone cannot separate them. Kept per language because the two lists overlap
# ('de' is Dutch "the" but not a German word) and a merged list would
# misclassify.
TARGET_LANGUAGE_MARKERS = {
    "de": {
        "ist", "sind", "bin", "bist", "ein", "eine", "der", "die", "das",
        "und", "wo", "ich", "du", "komme", "aus", "mein", "meine", "nicht",
    },
    "nl": {
        "is", "zijn", "een", "de", "het", "en", "ik", "je", "jij", "jullie",
        "heb", "hebt", "hebben", "wij", "zij", "hij", "niet",
    },
}

# German articles, and the Dutch pair. Used to split an article off the front of
# a headword so gender lands in its own column rather than being buried in the
# lemma text.
ARTICLES = {
    "de": {"der": "m", "die": "f", "das": "n"},
    # Dutch collapsed masculine and feminine into the common gender 'de', with
    # 'het' for neuter. Recorded as 'c' and 'n' rather than forced into the
    # German scheme, because the schema is meant to stay language-agnostic.
    "nl": {"de": "c", "het": "n"},
}

# Category nodes that describe grammar rather than a semantic field. Their
# descendants are function words, which make poor typing drills ("the" has three
# German answers). They are still worth ingesting as reference content; the
# decision about whether to drill them is made when item_state rows are created,
# not here.
FUNCTION_WORD_SECTIONS = {"Function Words", "Function words", "Rules"}

# Explicit list of the organising labels used in these two mindmaps. A purely
# structural rule cannot separate them from vocabulary: "Food" and "sein" both
# sit at the same depth with only leaf children beneath them. Since this script
# targets two specific hand-made files rather than arbitrary mindmaps, naming
# the categories is more honest and more reliable than a heuristic that would
# silently misfile a word.
CATEGORY_LABELS = {
    # Top level
    "Rules", "Word Tree", "Verbs", "Nouns", "Adjectives", "Adverbs",
    "Directions", "People", "Introductions", "Function Words",
    "Function words", "IPA Alphabet",
    # Semantic fields under Nouns
    "Food", "Places", "Objects", "Professions",
    # Grammatical fields under Function Words
    "Articles", "Pronouns", "Possessive adjectives", "Interrogatives",
    "Conjunctions", "Prepositions", "Particles", "Greetings",
}


def is_pronunciation(text: str) -> bool:
    """A child node that is a pronunciation hint rather than a meaning."""
    return bool(PRONUNCIATION_RE.match(text.strip()))


def is_target_language(text: str, language_code: str) -> bool:
    """A child node that is target-language text (an example sentence).

    Requires both several words and at least one target-language function word,
    because either signal alone produces false positives: English translations
    are often multi-word, and single target words appear as related-word nodes.
    """
    words = re.findall(r"[\wÀ-ɏ]+", text.lower())
    if len(words) < 2:
        return False
    markers = TARGET_LANGUAGE_MARKERS.get(language_code, set())
    return any(word in markers for word in words)


def split_article(headword: str, language_code: str) -> tuple[str, str, str]:
    """Split a leading article off a headword.

    Returns (article, lemma, gender). Gender is derived from the article, which
    is the only place the mindmap records it. Returns empty strings when there
    is no article, which is correct for verbs, adjectives and most function
    words rather than an error.
    """
    parts = headword.strip().split(None, 1)
    if len(parts) == 2:
        candidate = parts[0].lower()
        articles = ARTICLES.get(language_code, {})
        if candidate in articles:
            return parts[0], parts[1], articles[candidate]
    return "", headword.strip(), ""


def flag_row(lemma: str, gender: str, part_of_speech: str, translation: str) -> list[str]:
    """Collect review flags. These mark rows a human must look at, not errors.

    The point of this column is to make the review pass targeted rather than a
    full re-read of 150 rows.
    """
    flags = []

    # German nouns are capitalised. The mindmap notes this rule and then breaks
    # it constantly ("die pizza", "der kase"). Flagged rather than auto-fixed:
    # silently correcting text is how a wrong correction gets baked in unseen.
    if part_of_speech == "noun" and gender and lemma[:1].islower():
        flags.append("lowercase-noun")

    # A noun with no article in the source has no recorded gender, and gender
    # cannot be guessed. These need looking up before they are drillable.
    if part_of_speech == "noun" and not gender:
        flags.append("no-gender")

    # Nothing to prompt with. The typing exercise shows English and expects the
    # target language back, so a row without a translation cannot become a card.
    if not translation:
        flags.append("no-translation")

    # A slash usually means the node holds several inflected forms in one line
    # ("drinkt / drink / drinken", "lehrer / lehrerin"). Needs a decision: one
    # lexical item with variants, or several items.
    if "/" in lemma:
        flags.append("multiple-forms")

    return flags


def guess_part_of_speech(section: str, subsection: str, gender: str) -> str:
    """Infer part of speech from the mindmap's own category structure.

    The mindmap is organised by part of speech at the top level (Verbs, Nouns,
    Adjectives) and by semantic field below it (Food, Places, Objects), so the
    structure carries this for free.
    """
    section_map = {
        "Verbs": "verb",
        "Nouns": "noun",
        "Adjectives": "adjective",
        "Adverbs": "adverb",
        "Directions": "adverb",
        "People": "noun",
        "Introductions": "phrase",
    }
    if section in section_map:
        return section_map[section]

    # Inside Function Words the subsection is the part of speech.
    subsection_map = {
        "Articles": "article",
        "Pronouns": "pronoun",
        "Prepositions": "preposition",
        "Conjunctions": "conjunction",
        "Adverbs": "adverb",
        "Interrogatives": "interrogative",
        "Possessive adjectives": "possessive",
        "Particles": "particle",
    }
    if subsection in subsection_map:
        return subsection_map[subsection]

    # A gendered headword is a noun regardless of where it sits.
    return "noun" if gender else ""


def parse(path: Path, language_code: str) -> list[dict]:
    """Walk the mindmap and emit one row per vocabulary entry."""
    root = ET.parse(path).getroot()
    rows: list[dict] = []

    def walk(node, trail: list[str]) -> None:
        """Recurse, tracking the category trail above the current node."""
        text = (node.get("TEXT") or "").strip()
        children = node.findall("node")

        if not text:
            for child in children:
                walk(child, trail)
            return

        # Category nodes contribute to the trail and emit no row of their own.
        if text in CATEGORY_LABELS or not trail:
            for child in children:
                walk(child, trail + [text])
            return

        # Everything else is a vocabulary entry. Its leaf children are its
        # glosses; any child that is itself a parent is a nested entry in its
        # own right ("der bahnhof" has "hauptbahnhof" beneath it, and the Dutch
        # "have" node holds a whole conjugation). Emit this node from its leaf
        # children, then recurse into the branching ones, so neither the parent
        # word nor its nested entries are lost.
        leaf_children = [c for c in children if not c.findall("node")]
        branch_children = [c for c in children if c.findall("node")]

        # trail is [map root, section, subsection, ...]. Drop the root. The
        # "Word Tree" node is a structural wrapper rather than a category the
        # learner thinks in, so it is skipped when naming the section.
        path_parts = [p for p in trail[1:] if p != "Word Tree"]
        section = path_parts[0] if path_parts else ""
        subsection = path_parts[1] if len(path_parts) > 1 else ""

        article, lemma, gender = split_article(text, language_code)
        part_of_speech = guess_part_of_speech(section, subsection, gender)

        # Sort the leaf children into their kinds.
        pronunciations: list[str] = []
        sentences: list[str] = []
        others: list[str] = []
        for child in leaf_children:
            child_text = (child.get("TEXT") or "").strip()
            if not child_text:
                continue
            if is_pronunciation(child_text):
                pronunciations.append(child_text)
            elif is_target_language(child_text, language_code):
                sentences.append(child_text)
            else:
                others.append(child_text)

        # The first unclassified child is almost always the English gloss. The
        # rest are kept verbatim in their own column for the reviewer rather
        # than discarded, because they hold real content: related words, grammar
        # notes, plural forms.
        translation = others[0] if others else ""
        remaining = others[1:]

        rows.append({
            "section": section,
            "subsection": subsection,
            "is_function_word": "yes" if section in FUNCTION_WORD_SECTIONS else "",
            "article": article,
            "lemma": lemma,
            "gender": gender,
            "part_of_speech": part_of_speech,
            "translation_en": translation,
            "pronunciation": " | ".join(pronunciations),
            "example_sentences": " | ".join(sentences),
            "other_children": " | ".join(remaining),
            "flags": ",".join(flag_row(lemma, gender, part_of_speech, translation)),
        })

        # Nested entries below this word, e.g. hauptbahnhof under der bahnhof.
        for child in branch_children:
            walk(child, trail + [text])

    for top in root.findall("node"):
        walk(top, [])
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mindmap", type=Path)
    parser.add_argument(
        "--language",
        default="de",
        help="Language code of the mindmap's content (default: de)",
    )
    args = parser.parse_args()

    rows = parse(args.mindmap, args.language)
    if not rows:
        print("no rows parsed", file=sys.stderr)
        return 1

    columns = list(rows[0].keys())

    # TSV rather than CSV because the content contains commas and slashes but no
    # tabs, so no quoting or escaping is needed and the file stays readable and
    # diffable by eye.
    out = sys.stdout
    out.write("\t".join(columns) + "\n")
    for row in rows:
        out.write("\t".join(row[column].replace("\t", " ") for column in columns) + "\n")

    # Summary goes to stderr so it does not contaminate the redirected TSV.
    flagged = sum(1 for row in rows if row["flags"])
    sentences = sum(1 for row in rows if row["example_sentences"])
    print(
        f"{len(rows)} entries, {flagged} flagged for review, "
        f"{sentences} with example sentences",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
