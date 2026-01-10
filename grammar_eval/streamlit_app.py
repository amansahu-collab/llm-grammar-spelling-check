import streamlit as st
import requests
from core import evaluate_text  # local mode
import urllib3

API_URL = "http://127.0.0.1:8000/evaluate"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Grammar Evaluator", layout="wide")
st.title("📝 Grammar & Spelling Evaluator v1")

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
# Highlight grammar spans (AUTHORITATIVE)
# --------------------------------------------------
def highlight_grammar_spans(text, grammar_errors):
    html = text

    spans = [
        g["span"] for g in grammar_errors
        if isinstance(g, dict) and g.get("span")
    ]

    # 🔒 IMPORTANT: right-to-left to avoid index shift
    for span in sorted(spans, key=lambda x: x["start"], reverse=True):
        start, end = span["start"], span["end"]

        marked = (
            f"<span style='background:#ffd6d6;"
            f"padding:2px 4px;"
            f"border-radius:4px;"
            f"border-bottom:2px solid red;' "
            f"title='Grammar issue'>"
            f"{html[start:end]}"
            f"</span>"
        )

        html = html[:start] + marked + html[end:]

    return html


# --------------------------------------------------
# Highlight LLM diffs (fallback only)
# --------------------------------------------------
def highlight_text_with_feedback(original, diffs):
    html = original

    for d in sorted(diffs, key=lambda x: x["orig_span"][0], reverse=True):
        start, end = d["orig_span"]
        if start == end:
            continue

        color = {
            "replace": "#fff2cc",
            "delete": "#d9e8ff",
            "insert": "#d8f5e1"
        }.get(d["type"], "#eeeeee")

        corrected = d.get("corrected") or "removed"

        span = (
            f"<span style='background:{color};"
            f"padding:2px 4px;"
            f"border-radius:4px;"
            f"border-bottom:2px dotted #555;' "
            f"title='Suggestion: {corrected}'>"
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

            has_grammar_span = any(
                isinstance(g, dict) and g.get("span")
                for g in data["grammar_errors"]
            )

            if has_grammar_span:
                highlighted = highlight_grammar_spans(
                    data["original"], data["grammar_errors"]
                )
            else:
                highlighted = highlight_text_with_feedback(
                    data["original"], data["diffs"]
                )

            st.markdown(
                f"<div style='font-size:16px; line-height:1.6'>{highlighted}</div>",
                unsafe_allow_html=True
            )

        # ---------------------------
        # RIGHT: Evaluation
        # ---------------------------
        with col2:
            st.subheader("📊 Evaluation")
            st.metric("Final Score", data["score"])

            st.markdown("### Grammar & Usage Errors")

            if data["diffs"]:
                for d in data["diffs"]:
                    if d["type"] in ("replace", "insert", "delete"):
                        original = d["original"] or "(missing)"
                        corrected = d["corrected"] or "(removed)"
                        st.error(f"{original} → {corrected}")
            else:
                st.success("No errors detected")
            

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
