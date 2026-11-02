import logging
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)


def call_llm(prompt: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set (add it to .env)")

    client = OpenAI(api_key=api_key)
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    logger.info("Calling LLM model=%s (prompt length=%s)", model, len(prompt))
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.choices[0].message.content
    logger.info("LLM response length=%s", len(text) if text else 0)
    return text


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    prompt = "Are birds real?"
    print(call_llm(prompt))
