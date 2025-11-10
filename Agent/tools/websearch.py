# Agent/tools/websearch.py
from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import requests
from bs4 import BeautifulSoup

def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"

def _normalize_result(title: str, url: str) -> Dict[str, str]:
    return {"title": (title or "").strip()[:200], "url": (url or "").strip()[:500]}

def _serpapi_search(query: str, top_k: int) -> List[Dict[str, str]]:
    key = os.getenv("SERPAPI_KEY")
    if not key:
        return []
    endpoint = "https://serpapi.com/search.json"
    params = {"engine": "google", "q": query, "num": top_k, "api_key": key}
    r = requests.get(endpoint, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    out: List[Dict[str, str]] = []
    for item in (data.get("organic_results") or [])[:top_k]:
        title = item.get("title") or ""
        link = item.get("link") or ""
        if title and link:
            out.append(_normalize_result(title, link))
    return out

def _duckduckgo_html(query: str, top_k: int) -> List[Dict[str, str]]:
    """Try DuckDuckGo HTML search with better error handling"""
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        r = requests.post(url, data={"q": query, "b": ""}, timeout=15, headers=headers)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        out: List[Dict[str, str]] = []
        
        # Try multiple selectors
        for selector in [".result__a", ".links_main a", "a.result__url"]:
            for a in soup.select(selector):
                title = a.get_text(" ", strip=True)
                href = a.get("href") or ""
                if title and href and "http" in href:
                    out.append(_normalize_result(title, href))
                    if len(out) >= top_k:
                        break
            if out:
                break
        
        return out
    except Exception as e:
        print(f"DuckDuckGo search failed: {e}")
        return []

def _get_fallback_ats_keywords(query: str) -> List[Dict[str, str]]:
    """Provide built-in ATS keywords when web search fails"""
    query_lower = query.lower()
    
    # Common ATS keywords by category
    keywords = {
        "ai engineer": [
            "Machine Learning, Deep Learning, Neural Networks, TensorFlow, PyTorch",
            "Natural Language Processing (NLP), Computer Vision, LLMs, Transformers",
            "Python, R, SQL, Data Analysis, Model Training, Model Deployment",
            "LangChain, RAG, Prompt Engineering, Vector Databases, Embeddings",
            "AWS, Azure, GCP, Docker, Kubernetes, MLOps, CI/CD"
        ],
        "nlp": [
            "Natural Language Processing, Text Mining, Sentiment Analysis, Named Entity Recognition",
            "BERT, GPT, Transformers, Hugging Face, spaCy, NLTK",
            "Language Models, Text Classification, Information Extraction, Question Answering",
            "Tokenization, Word Embeddings, Attention Mechanisms, Sequence-to-Sequence"
        ],
        "llm": [
            "Large Language Models, GPT, BERT, LLaMA, Claude, Gemini",
            "Prompt Engineering, Few-Shot Learning, Fine-Tuning, RLHF",
            "LangChain, LlamaIndex, Vector Databases, RAG (Retrieval-Augmented Generation)",
            "OpenAI API, Anthropic API, Model Evaluation, Hallucination Mitigation"
        ],
        "action verbs": [
            "Developed, Engineered, Implemented, Designed, Architected, Built",
            "Optimized, Enhanced, Improved, Increased, Reduced, Streamlined",
            "Led, Managed, Coordinated, Collaborated, Mentored, Trained",
            "Analyzed, Evaluated, Assessed, Researched, Investigated, Tested"
        ]
    }
    
    # Find matching keywords
    results = []
    for category, keyword_list in keywords.items():
        if category in query_lower:
            for i, kw in enumerate(keyword_list):
                results.append({
                    "title": f"ATS Keywords: {kw}",
                    "url": f"built-in-keywords-{category}-{i}"
                })
    
    # If no specific match, return general AI/ML keywords
    if not results:
        results = [
            {"title": "Core AI/ML: Machine Learning, Deep Learning, Neural Networks, TensorFlow, PyTorch, Scikit-learn", "url": "built-in-ai-ml"},
            {"title": "NLP/LLM: Natural Language Processing, Large Language Models, Transformers, BERT, GPT, LangChain", "url": "built-in-nlp"},
            {"title": "Data: Python, SQL, Data Analysis, Feature Engineering, Model Training, Model Evaluation", "url": "built-in-data"},
            {"title": "Cloud/DevOps: AWS, Azure, Docker, Kubernetes, CI/CD, MLOps, Model Deployment", "url": "built-in-cloud"},
            {"title": "Action Verbs: Developed, Engineered, Optimized, Implemented, Designed, Led, Analyzed", "url": "built-in-verbs"}
        ]
    
    return results[:5]

def web_search(query: str, top_k: int = 5) -> Dict[str, Any]:
    trace: List[Dict[str, Any]] = [{"type": "search", "at": _now(), "query": query}]
    results: List[Dict[str, str]] = []
    provider: Optional[str] = None
    
    print(f"🔍 Web search requested: '{query}'")
    
    try:
        serp = _serpapi_search(query, top_k)
        if serp:
            provider = "serpapi"
            results = serp
            print(f"✓ Using SERPAPI - found {len(results)} results")
        else:
            provider = "duckduckgo"
            results = _duckduckgo_html(query, top_k)
            print(f"✓ Using DuckDuckGo - found {len(results)} results")
    except Exception as e:
        trace.append({"type": "note", "at": _now(), "text": f"Search error: {e}"})
        results = []
        print(f"✗ Web search failed: {e}")

    # Fallback to built-in keywords if search failed
    if not results:
        provider = "built-in-keywords"
        results = _get_fallback_ats_keywords(query)
        trace.append({"type": "note", "at": _now(), "text": "⚠️ Web search unavailable - using built-in ATS keyword database"})
        print(f"⚠️ Using fallback built-in keywords - found {len(results)} keyword sets")
    
    # Add provider info to the response
    trace.append({"type": "evidence", "at": _now(), "items": results[:top_k], "provider": provider or "none"})
    
    # Add a summary message that will be visible to the LLM
    summary = f"Search completed using {provider}. Found {len(results)} results."
    if provider == "built-in-keywords":
        summary += " (Note: These are curated ATS keywords since live web search is unavailable)"
    
    return {
        "_trace": trace, 
        "results": results[:top_k],
        "provider": provider,
        "summary": summary
    }
