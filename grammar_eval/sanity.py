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


def _extract_phrase_end(doc, phrase_tokens):
    """Get the end index of a phrase in the doc."""
    if phrase_tokens:
        last_token = phrase_tokens[-1]
        return last_token.idx + len(last_token.text)
    return 0


def _check_unnecessary_comma(text, doc):
    """
    Detect unnecessary commas using syntax:
    - Comma between subject and verb
    - Comma before restrictive relative clauses
    - Comma after coordinating conjunction
    """
    errors = []
    
    for token in doc:
        if token.text == ",":
            comma_idx = token.idx
            
            # Check 1: Comma between subject and verb
            # Subject (nsubj) should not have comma before verb
            before_comma = [t for t in doc if t.idx < token.idx]
            after_comma = [t for t in doc if t.idx > token.idx]
            
            if before_comma and after_comma:
                prev_token = before_comma[-1]
                next_token = after_comma[0]
                
                # If previous is a noun/subject and next is a verb
                if prev_token.dep_ in ("nsubj", "nsubjpass") and next_token.pos_ in ("VERB", "AUX"):
                    errors.append({
                        "type": "unnecessary_comma",
                        "span": {
                            "start": comma_idx,
                            "end": comma_idx + 1,
                            "text": ","
                        },
                        "message": "Unnecessary comma between subject and verb",
                        "suggestion": "Remove this comma"
                    })
                    continue
                
                # If next token is a relative pronoun with a restrictive clause
                # (restrictive clauses don't need commas)
                if next_token.text.lower() in ("that", "which", "who", "whom", "whose"):
                    # Check if this is restrictive (that/who) vs non-restrictive (which/whose)
                    if next_token.text.lower() == "that":
                        # "that" clauses are restrictive, comma is wrong
                        errors.append({
                            "type": "unnecessary_comma",
                            "span": {
                                "start": comma_idx,
                                "end": comma_idx + 1,
                                "text": ","
                            },
                            "message": "Comma before 'that' clause - use only for non-restrictive clauses",
                            "suggestion": "Remove comma before 'that'"
                        })
                        continue
                
                # If comma comes after a coordinating conjunction (double punct)
                if prev_token.pos_ == "CCONJ" and prev_token.text.lower() in ("and", "or", "but"):
                    errors.append({
                        "type": "unnecessary_comma",
                        "span": {
                            "start": comma_idx,
                            "end": comma_idx + 1,
                            "text": ","
                        },
                        "message": "Unnecessary comma after conjunction",
                        "suggestion": "Remove comma after conjunction"
                    })
    
    return errors


def _check_missing_comma(text, doc):
    """
    Detect missing commas using syntax and dependency parse:
    - Introductory clauses/phrases (prepositional, adverbial)
    - Non-restrictive relative clauses
    - Participial phrases
    
    EXCLUDES: appositive phrases, subjects with explanatory content
    """
    errors = []
    
    # Get ROOT verb
    root_verbs = [t for t in doc if t.dep_ == "ROOT"]
    if not root_verbs:
        return errors
    
    root_verb = root_verbs[0]
    
    # Find subject(s)
    subjects = [t for t in doc if t.dep_ in ("nsubj", "nsubjpass")]
    if not subjects:
        return errors
    
    subject = subjects[0]  # First subject
    subject_start = subject.idx
    
    # Build set of all tokens that are part of subject or its dependents
    # This includes: subject itself, appositives, and all their children
    subject_related = set(subjects)
    
    # Add appositive relations and all their descendants
    for token in doc:
        if token.dep_ == "appos" and any(token.head == s for s in subjects):
            subject_related.add(token)
    
    # Recursively add all dependents (children) of subject-related tokens
    changed = True
    while changed:
        changed = False
        for token in doc:
            if token.head in subject_related and token not in subject_related:
                subject_related.add(token)
                changed = True
    
    # Find true introductory elements:
    # - Come BEFORE subject
    # - Have introductory dependency (advmod, advcl, prep, mark, acl)
    # - Are NOT part of subject or appositive
    intro_candidates = []
    for token in doc:
        if token.idx < subject_start and token not in subject_related:
            if token.dep_ in ("advmod", "advcl", "prep", "mark", "acl"):
                intro_candidates.append(token)
    
    # If found an introductory element, check for missing comma
    if intro_candidates:
        last_intro = max(intro_candidates, key=lambda t: t.idx)
        intro_end = last_intro.idx + len(last_intro.text)
        
        # Check if comma exists between intro and subject
        text_between = text[intro_end:subject_start].lstrip()
        
        if text_between and text_between[0] != ",":
            errors.append({
                "type": "missing_comma_after_intro",
                "span": {
                    "start": intro_end,
                    "end": intro_end + 1,
                    "text": text[intro_end] if intro_end < len(text) else ""
                },
                "message": "Missing comma after introductory element",
                "suggestion": "Add a comma after the introductory phrase"
            })
    
    # Check for non-restrictive relative clauses (should have comma)
    for token in doc:
        if token.text.lower() in ("which", "whose") and token.pos_ == "PRON":
            # "which" and "whose" introduce non-restrictive clauses
            # Check if there's a comma before
            text_before = text[max(0, token.idx - 10):token.idx]
            
            if "," not in text_before:
                # This might be a non-restrictive clause without comma
                # Only flag if it's clearly non-restrictive (mid-sentence)
                if token.idx > 0:
                    errors.append({
                        "type": "missing_comma_before_nonrestrictive",
                        "span": {
                            "start": token.idx,
                            "end": token.idx + len(token.text),
                            "text": token.text
                        },
                        "message": f"Missing comma before non-restrictive '{token.text}' clause",
                        "suggestion": f"Add a comma before '{token.text}'"
                    })
    
    # Check for participial phrases (VBG) that modify clauses
    # Only flag TRUE participial clauses, NOT adjectival modifiers
    for token in doc:
        if token.pos_ == "VERB" and token.tag_ == "VBG":
            # SKIP if this is an adjectival modifier (amod)
            # These are lexicalized or compound adjectives like "awe-inspiring"
            if token.dep_ == "amod":
                continue
            
            # SKIP if this VBG is attached to a noun
            # (it's modifying the noun directly, not a clause)
            if token.head.pos_ == "NOUN":
                continue
            
            # ONLY flag if:
            # - Token is a clause modifier (advcl or acl)
            # - AND the head is ROOT (modifying main clause)
            # This indicates a true participial phrase needing comma
            if token.dep_ in ("advcl", "acl") and token.head.dep_ == "ROOT":
                # Participial phrase modifying main clause
                if token.idx > 0:
                    text_before = text[max(0, token.idx - 10):token.idx]
                    
                    # Check if comma precedes the participial phrase
                    if "," not in text_before and len(text_before) > 0 and text_before[-1] not in (" ", ","):
                        errors.append({
                            "type": "missing_comma_before_participle",
                            "span": {
                                "start": token.idx,
                                "end": token.idx + len(token.text),
                                "text": token.text
                            },
                            "message": f"Missing comma before participial phrase '{token.text}'",
                            "suggestion": f"Add a comma before '{token.text}' to set off the participial phrase"
                        })
    
    return errors


def _check_comma_spacing(text):
    """
    Detect comma spacing errors:
    - Space before comma
    - Missing space after comma
    """
    errors = []
    
    # Pattern 1: Space before comma
    for match in re.finditer(r'\s,', text):
        start = match.start()
        errors.append({
            "type": "space_before_comma",
            "span": {
                "start": start,
                "end": start + 2,
                "text": text[start:start+2]
            },
            "message": "Space before comma",
            "suggestion": "Remove space before comma"
        })
    
    # Pattern 2: Comma not followed by space (unless end of string or already space)
    for match in re.finditer(r',(?! |$)', text):
        comma_idx = match.start()
        if comma_idx + 1 < len(text) and text[comma_idx + 1] not in (" ", "\n"):
            errors.append({
                "type": "missing_space_after_comma",
                "span": {
                    "start": comma_idx,
                    "end": comma_idx + 2,
                    "text": text[comma_idx:comma_idx+2]
                },
                "message": "Missing space after comma",
                "suggestion": "Add space after comma"
            })
    
    return errors


def _check_run_on_sentence(text, doc):
    """
    Detect run-on sentences:
    - Multiple independent clauses without proper conjunction or punctuation
    - Based on dependency parse: multiple ROOT-level verbs
    """
    errors = []
    
    # Count verbs at ROOT level (independent clauses)
    root_verbs = [t for t in doc if t.dep_ == "ROOT"]
    
    # If multiple ROOTs, it's likely a run-on (should be separate sentences)
    if len(root_verbs) > 1:
        # Flag the second ROOT
        second_root = root_verbs[1]
        
        # Check if there's a coordinating conjunction connecting them
        has_conjunction = any(
            t.pos_ == "CCONJ" and t.idx < second_root.idx 
            for t in doc
        )
        
        if not has_conjunction:
            errors.append({
                "type": "run_on_sentence",
                "span": {
                    "start": second_root.idx,
                    "end": second_root.idx + len(second_root.text),
                    "text": second_root.text
                },
                "message": "Run-on sentence - multiple independent clauses",
                "suggestion": "Split into two sentences or add a coordinating conjunction"
            })
    
    # Also check for very long sentences with multiple verbs and no punctuation
    elif len(doc) > 25:
        # Count all verbs
        verbs = [t for t in doc if t.pos_ in ("VERB", "AUX")]
        
        if len(verbs) >= 2:
            # Check if there's proper coordination
            has_proper_junction = any(t.pos_ == "CCONJ" for t in doc) or any(t.text == ";" for t in doc)
            
            if not has_proper_junction:
                # Flag as potential run-on
                if len(verbs) > 1:
                    second_verb = verbs[1]
                    errors.append({
                        "type": "possible_run_on_sentence",
                        "span": {
                            "start": second_verb.idx,
                            "end": second_verb.idx + len(second_verb.text),
                            "text": second_verb.text
                        },
                        "message": "Possible run-on sentence - consider breaking into multiple sentences",
                        "suggestion": "Split sentence or add proper punctuation/conjunction"
                    })
    
    return errors


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
        # Find first token as anchor for missing_subject span
        if len(doc) > 0:
            first_token = doc[0]
            grammar_errors.append({
                "type": "missing_subject",
                "span": {
                    "start": first_token.idx,
                    "end": first_token.idx + len(first_token.text),
                    "text": first_token.text
                },
                "message": "Missing subject",
                "suggestion": "Add a subject to the sentence"
            })

    if not has_verb:
        # Find first token as anchor for missing_verb span
        if len(doc) > 0:
            first_token = doc[0]
            grammar_errors.append({
                "type": "missing_verb",
                "span": {
                    "start": first_token.idx,
                    "end": first_token.idx + len(first_token.text),
                    "text": first_token.text
                },
                "message": "Missing verb",
                "suggestion": "Add a verb to the sentence"
            })

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
            },
            "message": "Tense mismatch",
            "suggestion": f"Use future tense verb instead of '{verb_token.text}'"
        })

    # ==================================================
    # 5. Punctuation Rules (Logic-based, no hardcoding)
    # ==================================================
    
    # 5a. Unnecessary commas (syntax-based detection)
    unnecessary_comma_errors = _check_unnecessary_comma(text, doc)
    mechanics_errors.extend(unnecessary_comma_errors)
    
    # 5b. Missing commas (dependency parse-based detection)
    missing_comma_errors = _check_missing_comma(text, doc)
    mechanics_errors.extend(missing_comma_errors)
    
    # 5c. Comma spacing errors (regex + structure)
    comma_spacing_errors = _check_comma_spacing(text)
    mechanics_errors.extend(comma_spacing_errors)
    
    # 5d. Run-on sentences (dependency parse: multiple ROOT verbs)
    runon_errors = _check_run_on_sentence(text, doc)
    grammar_errors.extend(runon_errors)

    # ==================================================
    # 6. Basic Mechanics (unchanged, low severity)
    # ==================================================
    string_mechanics = []
    
    if text and text[0].islower():
        string_mechanics.append("capitalization")

    if re.search(r"[^\S\n]{2,}", text):
        string_mechanics.append("extra_whitespace")

    if re.search(r"\s+[,.!?;:]", text):
        string_mechanics.append("punctuation_spacing")

    if re.search(r"[,.!?;:][A-Za-z]", text):
        string_mechanics.append("punctuation_spacing")

    if not re.search(r"[.!?]$", text.strip()):
        string_mechanics.append("missing_punctuation")

    # Combine: dedup string errors, keep span-based errors
    mechanics_errors.extend(list(set(string_mechanics)))

    return grammar_errors, mechanics_errors
