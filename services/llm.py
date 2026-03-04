"""OpenRouter LLM Integration for book metadata extraction."""

import json
import os
from openai import AsyncOpenAI

OPEN_ROUTER_KEY = os.getenv("OPEN_ROUTER_KEY")

_client: AsyncOpenAI | None = None

def get_llm_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not OPEN_ROUTER_KEY:
            raise ValueError("OPEN_ROUTER_KEY must be set in .env")
        _client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPEN_ROUTER_KEY,
        )
    return _client


async def analyze_book_cover(text_content: str) -> dict:
    """
    Analyze the raw text of the first few pages of a book to determine
    the standardized name and structural categories. Returns a dict with
    'name': str and 'categories': list[str].
    """
    client = get_llm_client()
    
    system_prompt = (
        "You are an expert librarian AI that standardizes book names. "
        "Given the raw text extracted from the first few pages of a PDF book, "
        "extract the book's title and author(s), and classify it into 2-4 broad categories. "
        "The standard name MUST strictly follow the format: 'Title - Author'. "
        "Rules for the standard name:\n"
        "- Use Title Case for the title.\n"
        "- Use ONLY the author's last name (e.g. 'Kleppmann' instead of 'Martin Kleppmann').\n"
        "- If there are two authors, use 'Auth1 & Auth2'. If more, use 'Auth1 et al.'.\n"
        "- Remove any subtitles, edition numbers, publication years, or publisher names from the title.\n"
        "Return the result STRICTLY as a valid JSON object with no markdown fences, containing:\n"
        "{ \"name\": \"Standardized Name\", \"categories\": [\"category1\", \"category2\"] }"
    )
    
    user_prompt = f"Here is the text from the first pages of the book:\n\n{text_content[:4000]}"
    
    response = await client.chat.completions.create(
        model="google/gemini-2.5-flash",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    raw_content = response.choices[0].message.content
    try:
        data = json.loads(raw_content)
        return {
            "name": data.get("name", "Unknown Title - Unknown Author"),
            "categories": data.get("categories", [])
        }
    except json.JSONDecodeError:
        print(f"Failed to decode LLM response: {raw_content}")
        return {"name": "Unknown", "categories": []}
