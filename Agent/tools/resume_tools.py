# Agent/tools/resume_tools.py
from __future__ import annotations
from typing import Dict, Any
import os
import time

from langchain_core.tools import tool
from Agent.tools.pdf_tools import execute_resume_optimization  # tolerant public API

def _default_output_path() -> str:
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(os.getcwd(), "optimized_resumes")
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, f"optimized_resume_{ts}.pdf")

@tool
def optimize_resume_sections(output_path: str = "",
                             optimized_markdown: str = "",
                             name: str = "",
                             title: str = "",
                             contact_line: str = "") -> Dict[str, Any]:
    """
    Generate a styled PDF from final Markdown using the tolerant PDF API.
    Returns: {"ok": True, "output_path": "..."} on success.
    """
    if not optimized_markdown or not optimized_markdown.strip():
        return {"ok": False, "error": "optimized_markdown is required"}

    if not output_path:
        output_path = _default_output_path()

    try:
        # execute_resume_optimization returns a string like "Saved optimized PDF to <path>"
        result = execute_resume_optimization(
            output_path=output_path,
            optimized_text_sections=optimized_markdown,  # string accepted (Markdown)
            name=name or "Candidate",
            title=title or None,
            contact_line=contact_line or "",
        )
        if isinstance(result, str):
            # Try to pull the path from the message
            # e.g., "Saved optimized PDF to /abs/path/file.pdf"
            marker = "Saved optimized PDF to "
            if marker in result:
                real_path = result.split(marker, 1)[1].strip()
                return {"ok": True, "output_path": real_path}
            # Fallback: if it's already a path-like string
            if result.lower().endswith(".pdf"):
                return {"ok": True, "output_path": result}
        if isinstance(result, dict) and result.get("ok") and result.get("output_path"):
            return {"ok": True, "output_path": result["output_path"]}
        # Last resort: return provided output_path
        return {"ok": True, "output_path": output_path}
    except Exception as e:
        return {"ok": False, "error": str(e)}
