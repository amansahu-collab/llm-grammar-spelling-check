import re
from difflib import SequenceMatcher

def tokenize(text):
    """
    Tokenize text into words + punctuation, keeping positions.
    """
    tokens = []
    for m in re.finditer(r"\w+|[^\w\s]", text):
        tokens.append({
            "text": m.group(),
            "start": m.start(),
            "end": m.end()
        })
    return tokens


def diff_text(original: str, corrected: str):
    orig_tokens = tokenize(original)
    corr_tokens = tokenize(corrected)

    sm = SequenceMatcher(
        None,
        [t["text"] for t in orig_tokens],
        [t["text"] for t in corr_tokens],
    )

    diffs = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue

        # original span
        if i1 < len(orig_tokens):
            start = orig_tokens[i1]["start"]
            end = orig_tokens[i2 - 1]["end"]
            original_text = original[start:end]
        else:
            start = end = orig_tokens[-1]["end"]
            original_text = ""

        corrected_text = " ".join(
            t["text"] for t in corr_tokens[j1:j2]
        )

        diffs.append({
            "type": tag,
            "original": original_text,
            "corrected": corrected_text,
            "orig_span": (start, end),
        })

    return diffs
