"""Generate concise summaries of book excerpt text via OpenRouter."""

import os

from openai import AsyncOpenAI

OPEN_ROUTER_EMAIL_SUMMARY_GENERATOR_KEY = os.getenv("OPEN_ROUTER_EMAIL_SUMMARY_GENERATOR_KEY")
OPEN_ROUTER_EMAIL_SUMMARY_GENERATOR_MODEL = os.getenv(
    "OPEN_ROUTER_EMAIL_SUMMARY_GENERATOR_MODEL",
    "liquid/lfm-2.5-1.2b-thinking:free",
)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        key = OPEN_ROUTER_EMAIL_SUMMARY_GENERATOR_KEY
        if not key:
            raise ValueError("OPEN_ROUTER_EMAIL_SUMMARY_GENERATOR_KEY must be set in .env")
        _client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=key,
        )
    return _client


async def generate_excerpt_summary(text: str) -> str:
    """Return a concise summary of the given excerpt text."""
    client = _get_client()

    response = await client.chat.completions.create(
        model=OPEN_ROUTER_EMAIL_SUMMARY_GENERATOR_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an academic summarizer. "
                    "Summarize the following book excerpt in 8-12 sentences (approximately 250 words), "
                    "highlighting the key concepts and takeaways. "
                    "Write in the same language as the excerpt."
                ),
            },
            {"role": "user", "content": text[:12000]},
        ],
    )

    return response.choices[0].message.content.strip()
