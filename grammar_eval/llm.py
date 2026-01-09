import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

SYSTEM_PROMPT = """
You are a grammar correction engine.

STRICT RULES:
- Fix ONLY grammar, spelling, capitalization, commas, punctuation
- Do NOT rephrase
- Do NOT improve style
- Do NOT change sentence structure
- Do NOT add or remove sentences
- Preserve original wording as much as possible

Return ONLY the corrected text.
"""

def get_corrected_text(text: str) -> str:
    if not text.strip():
        return text

    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0,
        top_p=1,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ]
    )

    return resp.choices[0].message.content.strip()
