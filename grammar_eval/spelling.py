import re
from spellchecker import SpellChecker

spell = SpellChecker()

def check_spelling(text: str):
    """
    Check spelling and return misspelled words with their spans and suggestions.
    """
    misspelled_words = []
    misspelled_set = set()
    
    for match in re.finditer(r"\b[a-zA-Z]+\b", text):
        word = match.group()
        if word.lower() not in spell and word.lower() not in spell.known([word.lower()]):
            misspelled_set.add(word.lower())
            
            # Get correction suggestions from spellchecker
            suggestions = spell.candidates(word.lower())
            if not suggestions:
                suggestions = spell.known([word.lower()])
            
            suggestion = list(suggestions)[0] if suggestions else word.lower()
            
            misspelled_words.append({
                "word": word.lower(),
                "suggestion": suggestion,
                "span": {
                    "start": match.start(),
                    "end": match.end(),
                    "text": word
                }
            })
    
    return {
        "misspelled_words": misspelled_words,
        "misspelled_set": misspelled_set,
        "count": len(misspelled_set)
    }
