from llm import get_corrected_text
from diff_utils import diff_text
from sanity import sanity_check
from spelling import check_spelling
from scoring import compute_score


def evaluate_text(text: str) -> dict:
    original = text.strip()

    corrected = get_corrected_text(original)
    diffs = diff_text(original, corrected)

    grammar_errors, mechanics_errors = sanity_check(original, diffs)
    spelling = check_spelling(original)

    score = compute_score(diffs, mechanics_errors, spelling)

    return {
        "original": original,
        "corrected": corrected,
        "diffs": diffs,
        "grammar_errors": grammar_errors,
        "mechanics_errors": mechanics_errors,
        "spelling": spelling,
        "score": score
    }
