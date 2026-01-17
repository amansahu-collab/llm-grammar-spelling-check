def compute_score(grammar_errors, mechanics_errors, spelling):
    """
    Compute separate grammar and spelling scores as percentages (0-100%).
    
    Grammar Score (0-100%):
    - 100: No grammar errors
    - 0-99: Deductions based on error count
    
    Spelling Score (0-100%):
    - 100: No spelling errors
    - 0-99: Deductions based on misspelled word count
    """
    
    # --------------------
    # Grammar Score (0-100%)
    # --------------------
    g = len(grammar_errors)
    
    if g == 0:
        grammar_score = 100
    elif g <= 2:
        grammar_score = 75
    elif g <= 5:
        grammar_score = 50
    elif g <= 8:
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
