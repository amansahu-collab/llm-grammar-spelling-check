from llm import get_corrected_text
from diff_utils import diff_text
from sanity import sanity_check
from spelling import check_spelling
from scoring import compute_score


def _is_punctuation_only(text: str) -> bool:
    """Check if text contains only punctuation marks."""
    return text.strip() and all(c in ",.;:!?—-" for c in text.strip())


def _extract_punctuation_errors(original: str, diffs: list, existing_mechanics: list) -> list:
    """
    Extract punctuation-only diffs and convert them to mechanics errors.
    
    If a diff is insert/delete of ONLY punctuation:
    - Create a mechanics error with proper span
    - Avoid duplicating existing mechanics errors
    """
    punctuation_errors = []
    
    # Build set of existing punctuation error positions to avoid duplication
    existing_positions = set()
    for error in existing_mechanics:
        if isinstance(error, dict) and error.get("type") in ("unnecessary_comma", "space_before_comma", "missing_space_after_comma"):
            span = error.get("span")
            if span:
                existing_positions.add((span["start"], span["end"]))
    
    for diff in diffs:
        diff_type = diff.get("type")
        original_text = diff.get("original", "").strip()
        corrected_text = diff.get("corrected", "").strip()
        orig_span = diff.get("orig_span", (0, 0))
        
        # Check if this is a punctuation-only change
        is_punct_original = _is_punctuation_only(original_text)
        is_punct_corrected = _is_punctuation_only(corrected_text)
        
        if is_punct_original or is_punct_corrected:
            start, end = orig_span
            
            # Skip if this position already has a flagged error
            if (start, end) in existing_positions:
                continue
            
            # INSERT: Missing punctuation (corrected has punct, original doesn't)
            if diff_type == "insert" and is_punct_corrected and not is_punct_original:
                punctuation_errors.append({
                    "type": "punctuation_error",
                    "span": {
                        "start": start,
                        "end": end,
                        "text": original_text if original_text else ""
                    },
                    "message": f"Missing punctuation: '{corrected_text}'",
                    "suggestion": f"Add '{corrected_text}' here"
                })
            
            # DELETE: Unnecessary punctuation (original has punct, corrected doesn't)
            elif diff_type == "delete" and is_punct_original and not is_punct_corrected:
                punctuation_errors.append({
                    "type": "punctuation_error",
                    "span": {
                        "start": start,
                        "end": end,
                        "text": original_text
                    },
                    "message": f"Unnecessary punctuation: '{original_text}'",
                    "suggestion": f"Remove '{original_text}'"
                })
            
            # REPLACE: Punctuation swap (both are punct but different)
            elif diff_type == "replace" and is_punct_original and is_punct_corrected:
                punctuation_errors.append({
                    "type": "punctuation_error",
                    "span": {
                        "start": start,
                        "end": end,
                        "text": original_text
                    },
                    "message": f"Incorrect punctuation: '{original_text}' should be '{corrected_text}'",
                    "suggestion": f"Replace '{original_text}' with '{corrected_text}'"
                })
    
    return punctuation_errors


def evaluate_text(text: str) -> dict:
    original = text.strip()

    # Check grammar, mechanics, and spelling first
    grammar_errors, mechanics_errors = sanity_check(original, [])
    spelling = check_spelling(original)

    # Get LLM corrections and diffs (for reference only)
    corrected = get_corrected_text(original)
    all_diffs = diff_text(original, corrected)

    # Extract punctuation-only diffs and promote them to mechanics errors
    punctuation_errors = _extract_punctuation_errors(original, all_diffs, mechanics_errors)
    mechanics_errors.extend(punctuation_errors)

    # Filter diffs: exclude diffs that affect spelling errors or grammar/mechanics
    filtered_diffs = filter_diffs_for_ui(original, all_diffs, grammar_errors, mechanics_errors, spelling)

    # Compute scores based only on grammar, mechanics, and spelling
    scores = compute_score(grammar_errors, mechanics_errors, spelling)

    return {
        "original": original,
        "corrected": corrected,
        "diffs": filtered_diffs,
        "grammar_errors": grammar_errors,
        "mechanics_errors": mechanics_errors,
        "spelling": spelling,
        "scores": scores
    }


def filter_diffs_for_ui(original: str, diffs: list, grammar_errors: list, mechanics_errors: list, spelling: dict):
    """
    Filter LLM diffs to only show suggestions that don't conflict with:
    - Existing grammar errors
    - Existing mechanics errors
    - Spelling errors
    
    LLM diffs are assistive only and should not be shown when
    authoritative errors already cover the text.
    """
    # Collect all spans covered by grammar errors
    grammar_spans = set()
    for error in grammar_errors:
        if error.get("span"):
            start, end = error["span"]["start"], error["span"]["end"]
            for i in range(start, end):
                grammar_spans.add(i)

    # Collect all spans covered by mechanics errors (including promoted punctuation)
    mechanics_spans = set()
    for error in mechanics_errors:
        if isinstance(error, dict) and error.get("span"):
            start, end = error["span"]["start"], error["span"]["end"]
            for i in range(start, end):
                mechanics_spans.add(i)

    # Collect all positions covered by spelling errors
    spelling_spans = set()
    for word_info in spelling.get("misspelled_words", []):
        span = word_info.get("span")
        if span:
            start, end = span["start"], span["end"]
            for i in range(start, end):
                spelling_spans.add(i)

    filtered = []
    for diff in diffs:
        orig_span = diff.get("orig_span")
        if not orig_span or orig_span[0] >= orig_span[1]:
            continue

        start, end = orig_span
        
        # Skip if this diff overlaps with grammar errors
        has_grammar_conflict = any(i in grammar_spans for i in range(start, end))
        if has_grammar_conflict:
            continue

        # Skip if this diff overlaps with mechanics errors
        has_mechanics_conflict = any(i in mechanics_spans for i in range(start, end))
        if has_mechanics_conflict:
            continue

        # Skip if this diff overlaps with spelling errors
        has_spelling_conflict = any(i in spelling_spans for i in range(start, end))
        if has_spelling_conflict:
            continue

        filtered.append(diff)

    return filtered
