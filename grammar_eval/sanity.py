import re
import spacy

import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    # fallback (Streamlit Cloud safety)
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def sanity_check(text: str, diffs: list):
    grammar_errors = []
    mechanics_errors = []

    doc = nlp(text)

    # --- Grammar sanity (spaCy) ---
    has_subject = any(t.dep_ in ("nsubj", "nsubjpass") for t in doc)
    has_verb = any(t.pos_ in ("VERB", "AUX") for t in doc)

    if not has_subject:
        grammar_errors.append("missing_subject")
    if not has_verb:
        grammar_errors.append("missing_verb")

    # tense mismatch heuristic
    if re.search(r"\b(yesterday|last|ago)\b", text.lower()):
        for t in doc:
            if t.pos_ == "VERB" and t.tag_ in ("VB", "VBP", "VBZ"):
                grammar_errors.append("tense_error")
                break

    # --- Mechanics ---
    if text and text[0].islower():
        mechanics_errors.append("capitalization")

    if re.search(r"\s+[,.!?]", text):
        mechanics_errors.append("whitespace")

    if not re.search(r"[.!?]$", text.strip()):
        mechanics_errors.append("missing_punctuation")

    return list(set(grammar_errors)), list(set(mechanics_errors))
