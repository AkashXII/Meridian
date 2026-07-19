"""
One function, one job: hand back a configured chat model. Every node imports
this instead of constructing ChatGroq directly, so swapping providers or
models later (Kimi K2, a different provider, etc.) is a one-line change here,
not a search-and-replace across the codebase.
"""
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


def get_llm(temperature: float = 0):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY not set. Copy .env.example to .env and add your key."
        )
    model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    return ChatGroq(model=model_name, temperature=temperature, api_key=api_key)
