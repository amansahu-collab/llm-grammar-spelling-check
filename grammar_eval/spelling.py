import re
from spellchecker import SpellChecker

spell = SpellChecker()

def check_spelling(text: str):
    words = re.findall(r"\b[a-zA-Z]+\b", text)
    misspelled = spell.unknown(words)

    return {
        "misspelled_words": sorted(misspelled),
        "count": len(misspelled)
    }
