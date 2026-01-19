def compute_score(grammar_errors, mechanics_errors, spelling):
    """
    Compute grammar and spelling scores as percentages (0-100%).
    
    Grammar Score (0-100%):
    - Based on BOTH grammar errors AND mechanics errors
    - Mechanics errors are structural issues that reduce grammar quality
    - 100: No grammar or mechanics errors
    - 0-99: Deductions based on combined error count
    
    Spelling Score (0-100%):
    - Based only on spelling misspelled word count
    - 100: No spelling errors
    - 0-99: Deductions based on misspelled word count
    """
    
    # --------------------
    # Grammar Score (0-100%)
    # Combine grammar + mechanics (span-based only)
    # --------------------
    grammar_count = len(grammar_errors)
    
    # Count only span-based mechanics errors (dict with span)
    mechanics_span_errors = [e for e in mechanics_errors if isinstance(e, dict) and e.get("span")]
    mechanics_count = len(mechanics_span_errors)
    
    # Total errors affecting grammar quality
    total_errors = grammar_count + mechanics_count
    
    if total_errors == 0:
        grammar_score = 100
    elif total_errors <= 2:
        grammar_score = 75
    elif total_errors <= 5:
        grammar_score = 50
    elif total_errors <= 8:
        grammar_score = 25
    else:
        grammar_score = 0
    
    # --------------------
    # Spelling Score (0-100%)
    # --------------------
    s = spelling.get("count", 0)
    
    if s == 0:
        spelling_score = 100
    elif s <= 2:
        spelling_score = 75
    elif s <= 5:
        spelling_score = 50
    elif s <= 8:
        spelling_score = 25
    else:
        spelling_score = 0
    
    return {
        "grammar": grammar_score,
        "spelling": spelling_score
    }
