
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

def get_judge_llm():
    return ChatGroq(model="qwen/qwen3.6-27b", temperature=0)
def get_llm(temperature: float = 0):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY not set. Copy .env.example to .env and add your key."
        )
    model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    return ChatGroq(model=model_name, temperature=temperature, api_key=api_key)
