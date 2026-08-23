"""Generate the drafted German vocabulary TSV for human review.

The data below is hand-authored: translations filled in, prompts disambiguated,
genders and spellings corrected against the source mindmap. Held as tuples and
emitted as TSV rather than typed as a TSV by hand, so column alignment is
checked mechanically instead of by eye.

The `changes` column exists so the review pass can target what was altered
rather than re-reading every row. The learner does not speak German and cannot
verify this content from knowledge, so making the diffs visible is the whole
point.
"""

# Fields as held in ROWS below. answer_form is not among them: it is derived,
# because deriving it mechanically is safer than typing it 117 times, and the
# derivation is itself checkable.
FIELDS = [
    "lemma", "part_of_speech", "gender", "translation_en", "pronunciation",
    "category", "notes", "drillable", "source_text", "changes",
]

# Output column order, with the derived answer_form sitting next to the lemma it
# is built from so the two can be compared by eye during review.
COLUMNS = [
    "lemma", "answer_form", "part_of_speech", "gender", "translation_en",
    "pronunciation", "category", "notes", "drillable", "source_text", "changes",
]

# German nouns are learned with their article attached, so the expected answer
# is "das Haus", not "Haus". Mapping gender to the nominative definite article.
ARTICLE_BY_GENDER = {"m": "der", "f": "die", "n": "das"}

# Family members are learned with a possessive rather than an article: the unit
# is "mein Bruder", not "der Bruder". Kind is deliberately absent, because the
# source mindmap recorded it as "das Kind" and it is not a possessed relation in
# the same way.
POSSESSIVE_LEMMAS = {
    "Mama", "Papa", "Schwester", "Bruder", "Tochter", "Sohn", "Mann", "Frau",
}

# mein before masculine and neuter, meine before feminine. Derived from the
# gender column rather than written out per word, so the two cannot disagree.
POSSESSIVE_BY_GENDER = {"m": "mein", "f": "meine", "n": "mein"}


def answer_form_for(lemma: str, part_of_speech: str, gender: str) -> str:
    """The string the learner is expected to type.

    Returns an empty string when it is just the lemma, which is the case for
    verbs, adjectives, adverbs and phrases. Empty here becomes NULL in the
    database, and the exercise falls back to lemma.
    """
    if part_of_speech != "noun" or not gender:
        return ""
    if lemma in POSSESSIVE_LEMMAS:
        return f"{POSSESSIVE_BY_GENDER[gender]} {lemma}"
    return f"{ARTICLE_BY_GENDER[gender]} {lemma}"

# (lemma, pos, gender, translation_en, pronunciation, category, notes,
#  drillable, source_text, changes)
ROWS = [
    # --- Verbs ------------------------------------------------------------
    ("sein", "verb", "", "to be", "", "", "irregular: ich bin / du bist / er ist", "yes", "sein", ""),
    ("haben", "verb", "", "to have", "", "", "irregular: ich habe / du hast / er hat", "yes", "haben", ""),
    ("machen", "verb", "", "to make / to do", "", "", "regular", "yes", "machen", ""),
    ("gehen", "verb", "", "to go (on foot)", "", "", "contrast fahren, which is to go by vehicle", "yes", "gehen", "prompt disambiguated: bare 'to go' also fits fahren"),
    ("kommen", "verb", "", "to come", "", "", "irregular", "yes", "kommen", ""),
    ("sehen", "verb", "", "to see", "", "", "irregular: du siehst / er sieht", "yes", "sehen", ""),

    # --- Nouns: Food ------------------------------------------------------
    ("Pizza", "noun", "f", "the pizza", "", "Food", "plural: die Pizzas or die Pizzen", "yes", "die pizza", "capitalised"),
    ("Wurst", "noun", "f", "the sausage", "", "Food", "plural: die Wuerste (Würste)", "yes", "die wurst", "capitalised; translation added"),
    ("Käse", "noun", "m", "the cheese", "", "Food", "plural rare", "yes", "der kase", "spelling corrected to Käse; capitalised; translation added"),
    ("Salat", "noun", "m", "the salad / the lettuce", "", "Food", "plural: die Salate", "yes", "der salat", "capitalised; translation added"),
    ("Brot", "noun", "n", "the bread", "", "Food", "plural: die Brote", "yes", "das brot", "capitalised; translation added"),
    ("Schnitzel", "noun", "n", "the schnitzel / the cutlet", "", "Food", "plural: die Schnitzel, unchanged", "yes", "das schnitzel", "capitalised; translation added"),
    ("Zucker", "noun", "m", "the sugar", "", "Food", "no plural in normal use", "yes", "zucker", "gender added: der; capitalised; translation added"),
    ("Tee", "noun", "m", "the tea", "", "Food", "plural: die Tees", "yes", "tee", "gender added: der; capitalised; translation added"),
    ("Kaffee", "noun", "m", "the coffee", "", "Food", "plural: die Kaffees", "yes", "kaffee", "gender added: der; capitalised; translation added"),
    ("Keks", "noun", "m", "the biscuit / the cookie", "", "Food", "plural: die Kekse; the source gave the plural form", "yes", "kekse", "gender added: der; singular used as lemma; translation added"),
    ("Milch", "noun", "f", "the milk", "", "Food", "no plural in normal use", "yes", "milch", "gender added: die; capitalised; translation added"),
    ("Wasser", "noun", "n", "the water", "", "Food", "plural rare", "yes", "wasser", "gender added: das; capitalised; translation added"),

    # --- Nouns: Places ----------------------------------------------------
    ("Restaurant", "noun", "n", "the restaurant", "", "Places", "plural: die Restaurants", "yes", "das restaurant", "capitalised; translation added"),
    ("Hotel", "noun", "n", "the hotel", "", "Places", "plural: die Hotels", "yes", "das hotel", "capitalised; translation added"),
    ("Café", "noun", "n", "the cafe", "", "Places", "plural: die Cafés", "yes", "das café", "capitalised; translation added"),
    ("Stadt", "noun", "f", "the city / the town", "", "Places", "plural: die Staedte (Städte)", "yes", "die stadt", "capitalised; translation added"),
    ("Park", "noun", "m", "the park", "pah-k", "Places", "plural: die Parks", "yes", "der park", "capitalised; translation added"),
    ("Bahnhof", "noun", "m", "the railway station", "", "Places", "plural: die Bahnhoefe (Bahnhöfe)", "yes", "der bahnhof", "capitalised; translation added"),
    ("Hauptbahnhof", "noun", "m", "the central station", "", "Places", "Haupt- means main; plural: die Hauptbahnhoefe", "yes", "hauptbahnhof", "gender added: der; capitalised"),
    ("U-Bahn", "noun", "f", "the underground / the subway", "oo-baa-hn", "Places", "short for Untergrundbahn; plural: die U-Bahnen", "yes", "die U-bahn", "capitalisation corrected to U-Bahn; translation added"),
    ("Bibliothek", "noun", "f", "the library", "", "Places", "plural: die Bibliotheken", "yes", "die bibliotek", "spelling corrected to Bibliothek; capitalised; translation added"),
    ("Bäckerei", "noun", "f", "the bakery", "beck-a-rye", "Places", "plural: die Baeckereien (Bäckereien)", "yes", "die bäckerei", "capitalised; translation added"),
    ("Haus", "noun", "n", "the house", "", "Places", "plural: die Haeuser (Häuser)", "yes", "das Haus", ""),

    # --- Nouns: Objects ---------------------------------------------------
    ("Tisch", "noun", "m", "the table", "", "Objects", "plural: die Tische", "yes", "der Tisch", ""),
    ("Buch", "noun", "n", "the book", "", "Objects", "plural: die Buecher (Bücher)", "yes", "buch", "gender added: das; capitalised"),

    # --- Nouns: Professions -----------------------------------------------
    # Split into separate male and female entries. One card per answer: a
    # prompt of "the teacher" cannot decide between Lehrer and Lehrerin, and
    # would mark a correct answer wrong.
    ("Lehrer", "noun", "m", "the teacher (male)", "", "Professions", "plural: die Lehrer", "yes", "lehrer / lehrerin", "split into male and female entries; capitalised"),
    ("Lehrerin", "noun", "f", "the teacher (female)", "", "Professions", "plural: die Lehrerinnen", "yes", "lehrer / lehrerin", "split into male and female entries; capitalised"),
    ("Bäcker", "noun", "m", "the baker (male)", "becker", "Professions", "plural: die Baecker (Bäcker)", "yes", "bäcker / bäckerin", "split into male and female entries; capitalised"),
    ("Bäckerin", "noun", "f", "the baker (female)", "", "Professions", "plural: die Baeckerinnen", "yes", "bäcker / bäckerin", "split into male and female entries; capitalised"),
    ("Verkäufer", "noun", "m", "the shop assistant (male)", "", "Professions", "plural: die Verkaeufer (Verkäufer)", "yes", "verkäufer / verkäuferin", "split into male and female entries; capitalised"),
    ("Verkäuferin", "noun", "f", "the shop assistant (female)", "", "Professions", "plural: die Verkaeuferinnen", "yes", "verkäufer / verkäuferin", "split into male and female entries; capitalised"),
    ("Musiker", "noun", "m", "the musician (male)", "", "Professions", "plural: die Musiker", "yes", "musiker / musikerin", "split into male and female entries; capitalised"),
    ("Musikerin", "noun", "f", "the musician (female)", "", "Professions", "plural: die Musikerinnen", "yes", "musiker / musikerin", "split into male and female entries; capitalised"),

    # --- Adjectives -------------------------------------------------------
    ("frisch", "adjective", "", "fresh", "", "", "", "yes", "frisch", ""),
    ("billig", "adjective", "", "cheap", "", "", "", "yes", "billig", ""),
    ("nett", "adjective", "", "nice / kind (of a person)", "", "", "", "yes", "nett", "prompt disambiguated: the source glossed both nett and lecker as 'nice'"),
    ("lecker", "adjective", "", "tasty / delicious (of food)", "", "", "", "yes", "lecker", "translation corrected: the source said 'nice', which collided with nett"),
    ("neu", "adjective", "", "new", "", "", "", "yes", "neu", ""),
    ("schnell", "adjective", "", "fast / quick", "", "", "", "yes", "schnell", ""),
    ("satt", "adjective", "", "full (having eaten enough)", "", "", "only used of a person after eating; contrast voll, which is full of contents", "yes", "satt", "prompt disambiguated: bare 'full' would also fit voll"),
    ("hungrig", "adjective", "", "hungry", "", "", "", "yes", "hungrig", ""),
    ("groß", "adjective", "", "big / large", "", "", "", "yes", "groß", ""),
    ("alt", "adjective", "", "old", "", "", "", "yes", "alt", ""),
    ("schön", "adjective", "", "beautiful / lovely", "sh-or-n, where the or is long", "", "contrast schon, without the umlaut, which means already", "yes", "schön", "translation added: the source had only a pronunciation hint"),
    ("klein", "adjective", "", "small", "", "", "", "yes", "klein", ""),
    ("gut", "adjective", "", "good", "", "", "", "yes", "gut", ""),

    # --- Directions -------------------------------------------------------
    ("links", "adverb", "", "on the left", "", "Directions", "", "yes", "links", ""),
    ("rechts", "adverb", "", "on the right", "", "Directions", "", "yes", "rechts", ""),
    ("hier", "adverb", "", "here", "", "Directions", "", "yes", "hier", "the source listed hier twice, under Directions and under Adverbs; merged"),
    ("da drüben", "adverb", "", "over there", "", "Directions", "", "yes", "da drüben", ""),

    # --- People -----------------------------------------------------------
    # The lemma stays bare so gender has somewhere to live and joins stay clean,
    # but the answer_form carries the possessive, because that is the unit these
    # were actually learned as. See POSSESSIVE_LEMMAS below.
    ("Mama", "noun", "f", "my mum / my mummy", "", "People", "plain article form: die Mama", "yes", "meine mama", "translation added; possessive is the answer form"),
    ("Papa", "noun", "m", "my dad / my daddy", "", "People", "plain article form: der Papa", "yes", "mein papa", "translation added; possessive is the answer form"),
    ("Schwester", "noun", "f", "my sister", "", "People", "plain article form: die Schwester; plural: die Schwestern", "yes", "meine schwester", "translation added; possessive is the answer form"),
    ("Bruder", "noun", "m", "my brother", "", "People", "plain article form: der Bruder; plural: die Brueder (Brüder)", "yes", "mein bruder", "translation added; possessive is the answer form"),
    ("Tochter", "noun", "f", "my daughter", "", "People", "plain article form: die Tochter; plural: die Toechter (Töchter)", "yes", "meine tochter", "translation added; possessive is the answer form"),
    ("Sohn", "noun", "m", "my son", "zorn", "People", "plain article form: der Sohn; plural: die Soehne (Söhne)", "yes", "mein sohn", "translation added; possessive is the answer form"),
    ("Mann", "noun", "m", "my husband", "", "People", "der Mann on its own means the man; plural: die Maenner (Männer)", "yes", "mein mann", "possessive is the answer form"),
    ("Frau", "noun", "f", "my wife", "", "People", "die Frau on its own means the woman; plural: die Frauen", "yes", "meine frau", "possessive is the answer form"),
    ("Kind", "noun", "n", "the child", "", "People", "plural: die Kinder", "yes", "kind", "gender added: das; capitalised"),

    # --- Introductions (fixed phrases) ------------------------------------
    ("freut mich", "phrase", "", "nice to meet you", "", "Introductions", "literally 'pleases me'; short for es freut mich", "yes", "freut mich", ""),
    ("ich komme aus Berlin", "phrase", "", "I come from Berlin", "", "Introductions", "pattern: ich komme aus plus a place", "yes", "ich komme aus Berlin", "translation added"),
    ("ich bin David, und du?", "phrase", "", "I am David, and you?", "", "Introductions", "du is informal; use und Sie? when being formal", "yes", "ich bin David, und du?", "translation added"),
    ("bitte", "phrase", "", "please", "", "Introductions", "also means 'you are welcome' and 'here you are'", "yes", "bitte", "translation added; note records the other two meanings"),
    ("danke", "phrase", "", "thank you", "", "Introductions", "", "yes", "danke", "translation added"),
    ("tschüss", "phrase", "", "bye (informal)", "", "Introductions", "", "yes", "tschüss", "translation added, marked informal"),
    ("hallo", "phrase", "", "hello", "", "Introductions", "", "yes", "hallo", "translation added"),
    ("ja", "phrase", "", "yes", "", "Introductions", "", "yes", "ja", "translation added"),
    ("nein", "phrase", "", "no", "", "Introductions", "", "yes", "nein", "translation added"),

    # --- Function words ---------------------------------------------------
    # drillable = no. These are ingested as reference content but no item_state
    # row is created for them, so they never enter the due queue. English-to-
    # German typing cannot fairly test "the" when the answer is one of three.
    ("der", "article", "m", "the (masculine)", "", "", "", "no", "der", "prompt disambiguated: the source glossed der, die and das all as 'the'"),
    ("die", "article", "f", "the (feminine, and all plurals)", "", "", "", "no", "die", "prompt disambiguated"),
    ("das", "article", "n", "the (neuter)", "", "", "", "no", "das", "prompt disambiguated"),
    ("ein", "article", "", "a / an (before masculine and neuter)", "", "", "", "no", "ein", "prompt disambiguated"),
    ("eine", "article", "", "a / an (before feminine)", "", "", "", "no", "eine", "prompt disambiguated"),
    ("ich", "pronoun", "", "I", "", "", "", "no", "ich", ""),
    ("du", "pronoun", "", "you (singular, informal)", "", "", "", "no", "du", "prompt disambiguated from Sie"),
    ("er", "pronoun", "", "he", "", "", "", "no", "er", ""),
    ("sie", "pronoun", "", "she / they", "", "", "lowercase sie; capitalised Sie means you, formal", "no", "sie / Sie (formal)", "split from Sie; the source gloss omitted the formal 'you' entirely"),
    ("Sie", "pronoun", "", "you (formal)", "", "", "always capitalised", "no", "sie / Sie (formal)", "split from sie; the source gloss omitted this meaning"),
    ("wir", "pronoun", "", "we", "", "", "", "no", "wir", ""),
    ("mein", "possessive", "", "my (before masculine and neuter)", "", "", "", "no", "mein / meine", "split into two entries; prompt disambiguated"),
    ("meine", "possessive", "", "my (before feminine and plural)", "", "", "", "no", "mein / meine", "split into two entries; prompt disambiguated"),
    ("dein", "possessive", "", "your (before masculine and neuter)", "", "", "", "no", "dein / deine", "split into two entries; the source listed these under both Pronouns and Possessive adjectives"),
    ("deine", "possessive", "", "your (before feminine and plural)", "", "", "", "no", "dein / deine", "split into two entries; deduplicated"),
    ("wo", "interrogative", "", "where", "v-oh", "", "", "no", "wo", ""),
    ("und", "conjunction", "", "and", "", "", "", "no", "und", ""),
    ("aber", "conjunction", "", "but", "", "", "", "no", "aber", ""),
    ("denn", "conjunction", "", "because / for", "", "", "keeps normal word order, unlike weil", "no", "denn", "note added on the word order difference from weil"),
    ("weil", "conjunction", "", "because", "", "", "sends the verb to the end of the clause", "no", "weil", "note added"),
    ("dass", "conjunction", "", "that", "", "", "sends the verb to the end of the clause", "no", "dass", "note added"),
    ("wenn", "conjunction", "", "if / when", "", "", "", "no", "wenn", ""),
    ("obwohl", "conjunction", "", "although", "", "", "sends the verb to the end of the clause", "no", "obwohl", "note added"),
    ("oder", "conjunction", "", "or", "", "", "", "no", "oder", ""),
    ("ist", "verb", "", "is (he/she/it form of sein)", "", "", "", "no", "ist", "reclassified: the source filed this under Conjunctions, but it is a form of sein"),
    ("bist", "verb", "", "are (you form of sein)", "", "", "", "no", "bist", "reclassified: the source filed this under Conjunctions, but it is a form of sein"),
    ("in", "preposition", "", "in / into", "", "", "", "no", "in", ""),
    ("auf", "preposition", "", "on / onto", "", "", "", "no", "auf", ""),
    ("an", "preposition", "", "on / at (a vertical surface or an edge)", "", "", "", "no", "an", "prompt disambiguated from auf"),
    ("mit", "preposition", "", "with", "", "", "", "no", "mit", "the source listed mit twice, under Conjunctions and Prepositions; merged as a preposition"),
    ("von", "preposition", "", "from / of", "", "", "", "no", "von", ""),
    ("für", "preposition", "", "for", "", "", "", "no", "für", ""),
    ("zu", "preposition", "", "to / at", "", "", "", "no", "zu", ""),
    ("bei", "preposition", "", "at / by / with", "", "", "", "no", "bei", ""),
    ("nach", "preposition", "", "after / to", "", "", "", "no", "nach", ""),
    ("seit", "preposition", "", "since / for (a period of time)", "", "", "", "no", "seit", ""),
    ("heute", "adverb", "", "today", "", "", "", "no", "heute", ""),
    ("morgen", "adverb", "", "tomorrow", "", "", "lowercase morgen is tomorrow; capitalised der Morgen is the morning", "no", "morgen", "note added on the capitalisation difference"),
    ("gestern", "adverb", "", "yesterday", "", "", "", "no", "gestern", ""),
    ("dort", "adverb", "", "there", "", "", "", "no", "dort", ""),
    ("sehr", "adverb", "", "very", "", "", "", "no", "sehr", ""),
    ("nicht", "adverb", "", "not", "", "", "", "no", "nicht", ""),
    ("schon", "adverb", "", "already", "", "", "contrast schoen (schön), which means beautiful", "no", "schon", "note added"),
]

if __name__ == "__main__":
    import sys

    # Mechanical checks. The whole value of this file is that the learner cannot
    # check the German, so everything that CAN be checked by machine is.
    for index, row in enumerate(ROWS):
        assert len(row) == len(FIELDS), f"row {index} has {len(row)} fields, expected {len(FIELDS)}"
        assert not any("\t" in field for field in row), f"row {index} contains a tab"
        assert row[0], f"row {index} has an empty lemma"
        assert row[3], f"row {index} ({row[0]}) has no translation"
        assert row[7] in ("yes", "no"), f"row {index} has a bad drillable value"

    lemmas = [row[0] for row in ROWS]
    duplicates = {lemma for lemma in lemmas if lemmas.count(lemma) > 1}
    assert not duplicates, f"duplicate lemmas: {duplicates}"

    records = []
    for row in ROWS:
        record = dict(zip(FIELDS, row))
        record["answer_form"] = answer_form_for(
            record["lemma"], record["part_of_speech"], record["gender"]
        )
        records.append(record)

    # Every noun carrying a gender must end up with an article or possessive in
    # front of it. This is the check that catches a noun silently drilling as a
    # bare word, which is exactly the mistake being corrected here.
    for record in records:
        if record["part_of_speech"] == "noun" and record["gender"]:
            assert record["answer_form"].split()[0] in {"der", "die", "das", "mein", "meine"}, \
                f"{record['lemma']} has no determiner in its answer form"

    # Every possessive lemma must actually be a noun that exists in the batch,
    # so a typo in POSSESSIVE_LEMMAS fails loudly instead of silently doing
    # nothing.
    assert POSSESSIVE_LEMMAS <= set(lemmas), \
        f"POSSESSIVE_LEMMAS not in the batch: {POSSESSIVE_LEMMAS - set(lemmas)}"

    out = sys.stdout
    out.write("\t".join(COLUMNS) + "\n")
    for record in records:
        out.write("\t".join(record[column] for column in COLUMNS) + "\n")

    drillable = sum(1 for r in records if r["drillable"] == "yes")
    changed = sum(1 for r in records if r["changes"])
    with_form = sum(1 for r in records if r["answer_form"])
    print(
        f"{len(records)} entries, {drillable} drillable, {changed} with changes "
        f"to review, {with_form} with an answer form distinct from the lemma",
        file=sys.stderr,
    )
