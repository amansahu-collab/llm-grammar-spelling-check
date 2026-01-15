import re
import spacy

# ----------------------------
# spaCy safe load (local + cloud)
# ----------------------------
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# ----------------------------
# Time cue sets
# ----------------------------
PAST_CUES = {"yesterday", "ago", "last", "previous"}
FUTURE_CUES = {"tomorrow", "next", "soon", "upcoming"}


def sanity_check(text: str, diffs: list):
    grammar_errors = []
    mechanics_errors = []

    if not text.strip():
        return grammar_errors, mechanics_errors

    doc = nlp(text)
    text_lower = text.lower()

    # ==================================================
    # 1. Core sentence sanity
    # ==================================================
    has_subject = any(t.dep_ in ("nsubj", "nsubjpass") for t in doc)
    has_verb = any(t.pos_ in ("VERB", "AUX") for t in doc)

    if not has_subject:
        grammar_errors.append({"type": "missing_subject", "span": None})

    if not has_verb:
        grammar_errors.append({"type": "missing_verb", "span": None})

    # ==================================================
    # 2. Dynamic time-direction inference
    # ==================================================
    time_direction = "unknown"

    for ent in doc.ents:
        if ent.label_ == "DATE":
            if any(w in ent.text.lower() for w in PAST_CUES):
                time_direction = "past"
            elif any(w in ent.text.lower() for w in FUTURE_CUES):
                time_direction = "future"

    if time_direction == "unknown":
        if any(w in text_lower for w in PAST_CUES):
            time_direction = "past"
        elif any(w in text_lower for w in FUTURE_CUES):
            time_direction = "future"

    # ==================================================
    # 3. Verb time inference + blame token
    # ==================================================
    verb_token = None
    verb_time = "unknown"

    for t in doc:
        if t.lemma_ in ("will", "shall"):
            verb_time = "future"
            verb_token = t
            break

        if t.tag_ == "VBD":
            verb_time = "past"
            verb_token = t
            break

    # ==================================================
    # 4. Time compatibility checks (SPAN-BASED)
    # ==================================================
    if time_direction == "future" and verb_time == "past" and verb_token:
        grammar_errors.append({
            "type": "future_tense_error",
            "span": {
                "start": verb_token.idx,
                "end": verb_token.idx + len(verb_token.text),
                "text": verb_token.text
            }
        })

    # ---- tense_error logic commented out ----
    # if time_direction == "past":
    #     for t in doc:
    #         if t.pos_ == "VERB" and t.tag_ in ("VB", "VBP", "VBZ"):
    #             grammar_errors.append({
    #                 "type": "tense_error",
    #                 "span": {
    #                     "start": t.idx,
    #                     "end": t.idx + len(t.text),
    #                     "text": t.text
    #                 }
    #             })
    #             break

    # ==================================================
    # 5. Mechanics (unchanged, low severity)
    # ==================================================
    if text and text[0].islower():
        mechanics_errors.append("capitalization")

    if re.search(r"[^\S\n]{2,}", text):
        mechanics_errors.append("extra_whitespace")

    if re.search(r"\s+[,.!?;:]", text):
        mechanics_errors.append("punctuation_spacing")

    if re.search(r"[,.!?;:][A-Za-z]", text):
        mechanics_errors.append("punctuation_spacing")

    if not re.search(r"[.!?]$", text.strip()):
        mechanics_errors.append("missing_punctuation")

    return grammar_errors, list(set(mechanics_errors))
