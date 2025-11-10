# Agent/tools/websearch.py
from typing import Optional, List
from pydantic import BaseModel, Field
from langchain.tools import tool
import requests, re

class WebSearchInput(BaseModel):
    query: str = Field(..., description="Query to search")
    top_k: int = Field(5, ge=1, le=10)
    site: Optional[str] = Field(None, description="Optional domain filter like site:openai.com")

def _ddg_search(query: str, top_k: int, site: Optional[str]) -> List[dict]:
    """
    DuckDuckGo HTML fallback (no API key required).
    Returns minimal {title, url, snippet} entries.
    """
    q = f"{site} {query}".strip() if site else query.strip()
    r = requests.get("https://duckduckgo.com/html/", params={"q": q}, timeout=20)
    r.raise_for_status()
    html = r.text
    results = []

    for m in re.finditer(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.I | re.S):
        url = m.group(1)
        title = re.sub(r"<.*?>", "", m.group(2))
        tail = html[m.end(): m.end() + 1200]
        sn = re.search(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', tail, re.I | re.S)
        snippet = re.sub(r"<.*?>", "", sn.group(1)).strip() if sn else ""
        results.append({"title": title.strip(), "url": url.strip(), "snippet": snippet})
        if len(results) >= top_k:
            break
    return results

@tool("web_search", args_schema=WebSearchInput)
def web_search(query: str, top_k: int = 5, site: Optional[str] = None) -> str:
    """
    Performs a web search using DuckDuckGo HTML interface.
    Returns a compact JSON-like string list of {title,url,snippet}.
    """
    try:
        hits = _ddg_search(query, top_k, site)
        if not hits:
            return "[]"
        return "[" + ",".join(
            f'{{"title":"{h["title"]}","url":"{h["url"]}","snippet":"{h["snippet"]}"}}' for h in hits
        ) + "]"
    except Exception as e:
        return f'{{"error":"web_search_failed","detail":"{str(e)}"}}'
