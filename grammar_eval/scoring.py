import math

def compute_score(grammar_errors, mechanics_errors, spelling):
    """
    Practical scoring aligned with UI:

    Total score: 4

    Grammar / usage errors:
    - Based on number of corrections (diffs shown to user)
    - Max penalty: 2

    Spelling:
    - Based on misspelled word count
    - Max penalty: 1

    Mechanics:
    - Capitalization, spacing, punctuation
    - Max penalty: 1
    """

    score = 4.0

    # --------------------
    # 1. Grammar / usage penalty
    # --------------------
    g = len(grammar_errors)

    if g == 0:
        grammar_penalty = 0.0
    elif g <= 2:
        grammar_penalty = 0.5
    elif g <= 5:
        grammar_penalty = 1.0
    elif g <= 8:
        grammar_penalty = 1.5
    else:
        grammar_penalty = 2.0

    score -= grammar_penalty

    # --------------------
    # 2. Spelling penalty
    # --------------------
    s = spelling.get("count", 0)

    if s == 0:
        spelling_penalty = 0.0
    elif s <= 2:
        spelling_penalty = 0.5
    else:
        spelling_penalty = 1.0

    score -= spelling_penalty

    # --------------------
    # 3. Mechanics penalty
    # --------------------
    m = len(mechanics_errors)

    if m == 0:
        mechanics_penalty = 0.0
    elif m <= 2:
        mechanics_penalty = 0.25
    elif m <= 4:
        mechanics_penalty = 0.5
    else:
        mechanics_penalty = 1.0

    score -= mechanics_penalty

    # --------------------
    # Final score
    # --------------------
    # Round UP (benefit of doubt)
    return max(math.ceil(score), 0)
