"""
MCP Server for Book Gateway API.
Exposes endpoints to list books, get book content, request excerpts, and check job status.
"""

import os
import httpx
from typing import Any, List, Dict, Optional
from dotenv import load_dotenv

# Use FastMCP for rapid tool exposition
from mcp.server.fastmcp import FastMCP

load_dotenv()

MCP_SERVER_ADDRESS = os.getenv("MCP_SERVER_ADDRESS", "127.0.0.1")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8001"))
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

mcp = FastMCP("Book Gateway MCP Server")

@mcp.tool()
async def list_books() -> List[Dict[str, Any]]:
    """
    List all PDF books in the configured Google Drive folder.
    Returns details including file id, name, category, and availability.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/books")
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def get_book_content(file_id: str) -> Dict[str, Any]:
    """
    Returns the full text of the book as a structured JSON, page by page.
    This will trigger a lazy-download and extraction from Drive if it isn't cached yet.
    """
    timeout = httpx.Timeout(300.0) # Extraction could take a while
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(f"{BASE_URL}/books/{file_id}/content")
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def request_excerpt(file_id: str, start_page: int, end_page: int) -> Dict[str, Any]:
    """
    Triggers an excerpt generation job for a specified range of pages.
    Returns information about the created background job, including job_id.
    """
    payload = {
        "start": start_page,
        "end": end_page
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/books/{file_id}/excerpt", json=payload)
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def check_job_status(job_id: str) -> Dict[str, Any]:
    """
    Polls the status of an excerpt generation job using its job_id.
    Returns whether it's pending, ready, or encountered an error.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/jobs/{job_id}/status")
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def check_job_download(job_id: str) -> Dict[str, Any]:
    """
    Confirms the excerpt is ready and saved internally on the server 
    (the PDF is not returned directly, but its logical availability is).
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/jobs/{job_id}/download")
        response.raise_for_status()
        return response.json()

if __name__ == "__main__":
    # Start the SSE MCP Server using Uvicorn
    # Make sure you are using SSE mode as FastMCP relies on stdio by default.
    # We can programmatically run it via FastMCP's run() module.
    mcp.run(transport="sse", host=MCP_SERVER_ADDRESS, port=MCP_SERVER_PORT)
