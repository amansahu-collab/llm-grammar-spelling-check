"""import math

def compute_score(grammar, mechanics, spelling):
    score = 4.0

    # Grammar errors (major)
    if grammar:
        score -= 1
        if len(grammar) > 1:
            score -= 1

    # Mechanics errors (minor)
    if mechanics:
        score -= 0.5

    # Spelling errors
    if spelling["count"] > 0:
        score -= 1

    # Always round UP for fairness
    return max(math.ceil(score), 0)
"""


import math

def compute_score(grammar_errors, mechanics_errors, spelling):
    """
    Distributed scoring:
    - Total score: 4
    - Grammar max penalty: 2
    - Spelling max penalty: 1
    - Mechanics max penalty: 1
    """

    score = 4.0

    # --------------------
    # 1. Grammar penalty
    # --------------------
    g = len(grammar_errors)

    if g == 1:
        grammar_penalty = 1.0
    elif g in (2, 3):
        grammar_penalty = 1.5
    elif g >= 4:
        grammar_penalty = 2.0
    else:
        grammar_penalty = 0.0

    score -= grammar_penalty

    # --------------------
    # 2. Mechanics penalty
    # (caps, comma, space)
    # --------------------
    m = len(mechanics_errors)

    if m == 1:
        mechanics_penalty = 0.25
    elif m in (2, 3):
        mechanics_penalty = 0.5
    elif m >= 4:
        mechanics_penalty = 1.0
    else:
        mechanics_penalty = 0.0

    score -= mechanics_penalty

    # --------------------
    # 3. Spelling penalty
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
    # Final score
    # --------------------
    # Always round UP (benefit of doubt)
    return max(math.ceil(score), 0)
