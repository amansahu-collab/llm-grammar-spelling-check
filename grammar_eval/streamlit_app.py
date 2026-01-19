import streamlit as st
import requests
from core import evaluate_text  # local mode
import urllib3

API_URL = "http://127.0.0.1:8000/evaluate"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Grammar Evaluator", layout="wide")
st.title("📝 Grammar & Spelling Evaluator v2")

mode = st.radio(
    "Run mode",
    ["Local (no FastAPI)", "Via FastAPI"],
    horizontal=True
)

text = st.text_area(
    "Enter text",
    height=160,
    placeholder="Paste student response here..."
)


# --------------------------------------------------
# Single-pass highlighting with authority rules
# --------------------------------------------------
def build_highlighted_html(original_text, grammar_errors, mechanics_errors, spelling_errors, diffs):
    """
    Build highlighted HTML in a single pass.
    
    Authority order:
    1. Grammar/mechanics errors (red, solid underline) - AUTHORITATIVE
    2. Spelling errors (orange, solid underline) - AUTHORITATIVE at word level
    3. LLM diffs (yellow, dotted underline) - ASSISTIVE only
    
    No overlapping spans. Widest span wins.
    """
    
    # Collect all spans with their type and metadata
    all_spans = []
    
    # Grammar errors (highest priority)
    for error in grammar_errors:
        span = error.get("span")
        if span and span.get("start") is not None and span.get("end") is not None:
            if span["start"] < span["end"]:  # Valid span
                all_spans.append({
                    "start": span["start"],
                    "end": span["end"],
                    "type": "grammar",
                    "message": error.get("message", error.get("type", "")),
                    "suggestion": error.get("suggestion", "")
                })
    
    # Span-based mechanics errors (also red, same priority as grammar)
    for error in mechanics_errors:
        if isinstance(error, dict) and error.get("span"):
            span = error.get("span")
            if span and span.get("start") is not None and span.get("end") is not None:
                if span["start"] < span["end"]:
                    all_spans.append({
                        "start": span["start"],
                        "end": span["end"],
                        "type": "grammar",
                        "message": error.get("message", error.get("type", "")),
                        "suggestion": error.get("suggestion", "")
                    })
    
    # Spelling errors (word-level, owns full word)
    for word_info in spelling_errors:
        span = word_info.get("span")
        if span and span.get("start") is not None and span.get("end") is not None:
            if span["start"] < span["end"]:  # Valid span
                all_spans.append({
                    "start": span["start"],
                    "end": span["end"],
                    "type": "spelling",
                    "message": f"Spelling: {word_info.get('word', '')}",
                    "suggestion": word_info.get("suggestion", "")
                })
    
    # LLM diffs (only if no grammar/spelling overlap)
    grammar_spelling_spans = set()
    for sp in all_spans:
        for i in range(sp["start"], sp["end"]):
            grammar_spelling_spans.add(i)
    
    for diff in diffs:
        orig_span = diff.get("orig_span")
        if not orig_span or orig_span[0] >= orig_span[1]:
            continue
        
        start, end = orig_span
        
        # Check for overlap with grammar/spelling
        has_overlap = any(i in grammar_spelling_spans for i in range(start, end))
        if has_overlap:
            continue
        
        corrected = diff.get("corrected", "").strip()
        if not corrected or len(corrected) == 1 and not corrected.isalnum():
            continue
        
        all_spans.append({
            "start": start,
            "end": end,
            "type": "llm_diff",
            "message": f"Suggestion: {corrected}",
            "suggestion": corrected
        })
    
    # Sort spans by start position (ascending) and by length (descending) to handle nesting
    all_spans.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
    
    # Remove overlapping spans (keep wider/earlier spans)
    filtered_spans = []
    covered = set()
    
    for span in all_spans:
        start, end = span["start"], span["end"]
        
        # Check if this span overlaps with already-covered positions
        if any(i in covered for i in range(start, end)):
            continue
        
        filtered_spans.append(span)
        for i in range(start, end):
            covered.add(i)
    
    # Sort by start position (descending) for right-to-left insertion
    filtered_spans.sort(key=lambda x: x["start"], reverse=True)
    
    # Build HTML with single pass (right-to-left to avoid index shifts)
    html = original_text
    
    for span in filtered_spans:
        start = span["start"]
        end = span["end"]
        text_chunk = original_text[start:end]
        
        if span["type"] == "grammar":
            style = (
                "background:#ffd6d6;"
                "padding:2px 4px;"
                "border-radius:4px;"
                "border-bottom:2px solid red;"
                "cursor:help;"
            )
            title = span["message"]
            if span["suggestion"]:
                title += f" → {span['suggestion']}"
        
        elif span["type"] == "spelling":
            style = (
                "background:#ffe6cc;"
                "padding:2px 4px;"
                "border-radius:4px;"
                "border-bottom:2px solid #ff9800;"
                "cursor:help;"
            )
            title = span["message"]
            if span["suggestion"]:
                title += f" → {span['suggestion']}"
        
        else:  # llm_diff
            style = (
                "background:#fff2cc;"
                "padding:2px 4px;"
                "border-radius:4px;"
                "border-bottom:2px dotted #555;"
                "cursor:help;"
            )
            title = span["message"]
        
        marked = (
            f"<span style='{style}' title='{title}'>"
            f"{text_chunk}"
            f"</span>"
        )
        
        html = html[:start] + marked + html[end:]
    
    return html


if st.button("Evaluate"):
    if not text.strip():
        st.warning("Please enter some text.")
    else:
        with st.spinner("Analyzing..."):
            if mode == "Via FastAPI":
                resp = requests.post(API_URL, json={"text": text}, verify=False)
                data = resp.json()
            else:
                data = evaluate_text(text)

        col1, col2 = st.columns([2, 1])

        # ---------------------------
        # LEFT: Highlighted Text
        # ---------------------------
        with col1:
            st.subheader("📄 Highlighted Text")

            highlighted_html = build_highlighted_html(
                data["original"],
                data["grammar_errors"],
                data["mechanics_errors"],
                data["spelling"].get("misspelled_words", []),
                data["diffs"]
            )

            st.markdown(
                f"<div style='font-size:16px; line-height:1.6'>{highlighted_html}</div>",
                unsafe_allow_html=True
            )

        # ---------------------------
        # RIGHT: Evaluation
        # ---------------------------
        with col2:
            st.subheader("📊 Evaluation")
            
            # Display separate scores
            score_col1, score_col2 = st.columns(2)
            with score_col1:
                st.metric("Grammar Score", f"{data['scores']['grammar']}%")
            with score_col2:
                st.metric("Spelling Score", f"{data['scores']['spelling']}%")

            st.markdown("### Grammar & Usage Errors")

            if data["grammar_errors"]:
                for error in data["grammar_errors"]:
                    msg = error.get("message", error.get("type", "Grammar issue"))
                    sug = error.get("suggestion", "")
                    if sug:
                        st.error(f"{msg} → {sug}")
                    else:
                        st.error(msg)
            else:
                st.success("No grammar errors detected")

            st.markdown("### Mechanics")
            if data["mechanics_errors"]:
                for m in data["mechanics_errors"]:
                    if isinstance(m, dict):
                        # Span-based mechanics error
                        msg = m.get("message", m.get("type", "Mechanics issue"))
                        sug = m.get("suggestion", "")
                        if sug:
                            st.warning(f"{msg} → {sug}")
                        else:
                            st.warning(msg)
                    else:
                        # String-based mechanics error
                        st.warning(m)
            else:
                st.success("No mechanics issues")

            st.markdown("### Spelling")
            spelling_words = data["spelling"].get("misspelled_words", [])
            if spelling_words:
                for word_info in spelling_words:
                    word = word_info.get("word", word_info)
                    st.error(word)
            else:
                st.success("No spelling mistakes")

        with st.expander("🔍 Raw JSON"):
            st.json(data)
