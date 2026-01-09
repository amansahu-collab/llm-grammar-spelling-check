import streamlit as st
import requests
from core import evaluate_text  # local mode

API_URL = "http://127.0.0.1:8000/evaluate"

st.set_page_config(page_title="Grammar Evaluator", layout="wide")
st.title("📝 Grammar & Spelling Evaluator")

# 🔀 Mode switch
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

def highlight_text_with_feedback(original, diffs):
    """
    Highlight incorrect spans.
    Hover shows correction.
    No JS, safe HTML only.
    """

    html = original

    # IMPORTANT: apply diffs from right to left
    for d in sorted(diffs, key=lambda x: x["orig_span"][0], reverse=True):
        start, end = d["orig_span"]

        # Skip zero-length spans
        if start == end:
            continue

        color = {
            "replace": "#ffe0e0",   # red
            "delete": "#e0ecff",    # blue
            "insert": "#e0ffe8"     # green
        }.get(d["type"], "#eeeeee")

        corrected = d["corrected"] or "removed"

        span = (
            f"<span "
            f"style='background:{color}; "
            f"padding:2px 4px; "
            f"border-radius:4px; "
            f"border-bottom:2px dotted #555;' "
            f"title='Correct: {corrected}'>"
            f"{html[start:end]}"
            f"</span>"
        )

        html = html[:start] + span + html[end:]

    return html

if st.button("Evaluate"):
    if not text.strip():
        st.warning("Please enter some text.")
    else:
        with st.spinner("Analyzing..."):
            if mode == "Via FastAPI":
                resp = requests.post(API_URL, json={"text": text})
                data = resp.json()
            else:
                data = evaluate_text(text)

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("📄 Highlighted Text")
            highlighted = highlight_text_with_feedback(data["original"], data["diffs"])
            st.markdown(
                f"<div style='font-size:16px; line-height:1.6'>{highlighted}</div>",
                unsafe_allow_html=True
            )

        with col2:
            st.subheader("📊 Evaluation")
            st.metric("Final Score", data["score"])

            st.markdown("### Grammar Errors")
            if data["grammar_errors"]:
                for g in data["grammar_errors"]:
                    st.error(g)
            else:
                st.success("No grammar errors")

            st.markdown("### Mechanics")
            if data["mechanics_errors"]:
                for m in data["mechanics_errors"]:
                    st.warning(m)
            else:
                st.success("No mechanics issues")

            st.markdown("### Spelling")
            if data["spelling"]["count"] > 0:
                for w in data["spelling"]["misspelled_words"]:
                    st.error(w)
            else:
                st.success("No spelling mistakes")

        with st.expander("🔍 Raw JSON"):
            st.json(data)
