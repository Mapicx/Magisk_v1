# Backend/routers/Resume_getter.py
from __future__ import annotations
import io
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import fitz  # PyMuPDF
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

# --- Adjust these imports to match your project structure ---
from Agent.graph.graph_setup import build_graph
from Agent.utils.logging_utils import log_llm_operation

# If you use ORM/DB, re-add your real imports here (kept minimal for clarity)
# from Backend import models, database
# from sqlalchemy.orm import Session
# from fastapi import Depends

# -----------------------------------------------------------
# Setup
# -----------------------------------------------------------
router = APIRouter(tags=["Resume Optimizer"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OPTIMIZED_DIR = PROJECT_ROOT / "optimized_resumes"
OPTIMIZED_DIR.mkdir(exist_ok=True)

# compile graph once
chatbot = build_graph()


# -----------------------------------------------------------
# Helpers
# -----------------------------------------------------------
def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _safe_str(x: Any, maxlen: int = 1200) -> str:
    try:
        s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    except Exception:
        s = str(x)
    if len(s) > maxlen:
        s = s[:maxlen] + "…"
    return s


# redact some heavy fields so UI stays readable
REDACT_KEYS = {
    "optimized_markdown",
    "raw_html",
    "page_html",
    "content_blob",
    "raw_text",
    "html",
    "markdown",
}



def _sanitize_args(args: Any) -> Any:
    """
    Remove / shrink huge fields from tool call args so the frontend collapsible
    doesn't get spammed with megabytes of text.
    """
    if isinstance(args, dict):
        out = {}
        for k, v in args.items():
            if k in REDACT_KEYS:
                out[k] = "[[omitted large text]]"
            elif isinstance(v, str) and len(v) > 800:
                out[k] = _safe_str(v, 400)
            else:
                out[k] = v
        return out
    return args


def _result_to_messages(result: Any) -> List[Any]:
    """
    Normalize LangGraph result to a list of messages.
    Handles both:
      - dict with {"messages": [...]}
      - a raw list of messages
    """
    if isinstance(result, dict) and "messages" in result:
        msgs = result["messages"]
        if isinstance(msgs, list):
            return msgs
        # Sometimes libs return tuples/etc.
        return list(msgs)
    if isinstance(result, list):
        return result
    # last resort: wrap as a single assistant message
    return [AIMessage(content=_safe_str(result))]


def _expand_tool_result_content(content: Any) -> List[Dict[str, Any]]:
    """
    Expand a tool's return content into UI-friendly entries.
    If it contains {"_trace":[...]}, we expand that as the readable timeline.
    Otherwise, we add one 'note' entry with a compact preview.
    """
    entries: List[Dict[str, Any]] = []
    parsed = None

    if isinstance(content, (dict, list)):
        parsed = content
    elif isinstance(content, str):
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = None

    if isinstance(parsed, dict) and isinstance(parsed.get("_trace"), list):
        for item in parsed["_trace"]:
            if isinstance(item, dict):
                entries.append(
                    {
                        "type": item.get("type", "note"),
                        "at": item.get("at", _now_iso()),
                        **{k: v for k, v in item.items() if k not in {"type", "at"}},
                    }
                )
        # helpful summaries
        if isinstance(parsed.get("results"), list):
            entries.append(
                {
                    "type": "note",
                    "at": _now_iso(),
                    "text": f"{len(parsed['results'])} search results gathered.",
                }
            )
        if "output_path" in parsed:
            entries.append({"type": "file", "at": _now_iso(), "file": parsed["output_path"]})
    else:
        # fallback: compact preview
        entries.append({"type": "note", "at": _now_iso(), "text": _safe_str(content, 700)})

    return entries


def _build_tool_trace_and_response(messages: List[Any]) -> Tuple[str, bool, List[Dict[str, Any]], Optional[str]]:
    """
    Walk the entire message list to:
      - produce a 'tool_trace' timeline
      - determine 'tool_used'
      - pick the final assistant content
      - build a short, safe 'thinking_note'
    """
    tool_trace: List[Dict[str, Any]] = []
    tool_used = False
    ai_response = ""

    # Forward pass: capture tool calls + tool results
    for m in messages:
        # Tool calls from AIMessage
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            for tc in m.tool_calls:
                tool_trace.append(
                    {
                        "type": "call",
                        "at": _now_iso(),
                        "tool": tc.get("name"),
                        "args": _sanitize_args(tc.get("args", {})),
                    }
                )
            tool_used = True

        # Tool results (ToolMessage)
        if isinstance(m, ToolMessage) or getattr(m, "name", None) or getattr(m, "tool_call_id", None):
            name = getattr(m, "name", None)
            content = getattr(m, "content", "")
            expanded = _expand_tool_result_content(content)
            for e in expanded:
                tool_trace.append({"type": "result", "at": _now_iso(), "tool": name, **e})
            tool_used = True

    # Backward pass: pick last contentful assistant message as final text
    for m in reversed(messages):
        # prefer AIMessage content
        if isinstance(m, AIMessage) and getattr(m, "content", None):
            ai_response = m.content
            break
        # fallback to any message with 'content'
        if getattr(m, "content", None):
            ai_response = m.content
            break

    # compact, safe thinking note
    thinking_note = None
    tools = [x.get("tool") for x in tool_trace if x.get("type") == "call" and x.get("tool")]
    if tools:
        uniq: List[str] = []
        for t in tools:
            if t not in uniq:
                uniq.append(t)
        thinking_note = f"Used tools: {', '.join(uniq)}"

    return ai_response, tool_used, tool_trace, thinking_note
# -----------------------------------------------------------


@router.post("/optimize_resume")
async def optimize_resume(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    user_message: str = Form(...),
    thread_id: Optional[str] = Form(None),
    # db: Session = Depends(database.get_db),  # re-enable if you use a DB here
):
    """
    Main endpoint: extracts text, invokes the agent graph, returns AI reply + tool timeline.
    """

    # ---- 1) Validate + read PDF
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    raw = await file.read()
    log_llm_operation(
        "REQUEST_RECEIVED",
        {"endpoint": "/optimize_resume", "filename": file.filename, "bytes": len(raw), "thread_id": thread_id or "NEW"},
    )

    # ---- 2) Extract text
    try:
        resume_text = ""
        with fitz.open(stream=io.BytesIO(raw), filetype="pdf") as doc:
            pages = doc.page_count
            for page in doc:
                resume_text += page.get_text()  # type: ignore
        resume_text = resume_text.strip()
        log_llm_operation(
            "RESUME_TEXT_EXTRACTED",
            {"pages": pages, "text_len": len(resume_text), "thread_id": thread_id or "NEW"},
        )
    except Exception as e:
        log_llm_operation("RESUME_TEXT_EXTRACT_ERROR", {"error": str(e)}, success=False)
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {e}")

    # ---- 3) (Optional) DB save (restore your original code if you used ORM)
    # resume_entry = models.Resume(filename=file.filename, file_url="...")  # type: ignore
    # db.add(resume_entry); db.commit(); db.refresh(resume_entry)
    # log_llm_operation("DB_SAVE_OK", {"resume_id": resume_entry.id})

    # ---- 4) Invoke graph
    config_thread_id = thread_id or str(uuid.uuid4())
    config = {
        "configurable": {"thread_id": config_thread_id},
        "recursion_limit": 50  # Allow enough iterations for tool calls
    }
    inputs = {
        "messages": [HumanMessage(content=user_message)],
        "resume": resume_text,
        "job_description": job_description,
        "resume_file_name": file.filename,
    }

    log_llm_operation(
        "CHATBOT_INVOCATION_START",
        {
            "thread_id": config_thread_id,
            "has_thread": bool(thread_id),
            "user_message_len": len(user_message),
            "resume_len": len(resume_text),
            "jd_len": len(job_description),
        },
    )

    try:
        result = chatbot.invoke(inputs, config=config)  # shape: dict(messages=[...]) OR just [...]
    except Exception as e:
        log_llm_operation(
            "CHATBOT_INVOCATION_ERROR",
            {"thread_id": config_thread_id, "error": str(e)},
            success=False,
        )
        raise HTTPException(status_code=500, detail=f"AI processing failed: {e}")

    # ---- 5) Normalize + parse
    messages = _result_to_messages(result)
    ai_response, tool_used, tool_trace, thinking_note = _build_tool_trace_and_response(messages)

    log_llm_operation(
        "LLM_RESPONSE_COMPLETE",
        {
            "thread_id": config_thread_id,
            "ai_response_len": len(ai_response or ""),
            "tool_used": tool_used,
            "total_messages": len(messages),
        },
    )

    # ---- 6) Try to capture a filename from the AI text (for your current download button)
    optimized_file_name = None
    m = re.search(r"([^\s/]+_optimized_[^\s/]+\.pdf)", (ai_response or ""), re.IGNORECASE)
    if m:
        optimized_file_name = m.group(1)

    # ---- 7) Build response
    return {
        "thread_id": config_thread_id,
        "ai_response": ai_response,
        "tool_used": tool_used,
        "tool_trace": tool_trace,
        "thinking_note": thinking_note,
        "optimized_file_name": optimized_file_name,
        "optimized_file_exists": bool(optimized_file_name and (OPTIMIZED_DIR / optimized_file_name).exists()),
    }


@router.get("/download_optimized/{filename}")
def download_optimized(filename: str):
    """
    Serve an optimized resume by filename (must exist in OPTIMIZED_DIR).
    """
    path = OPTIMIZED_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(path), filename=filename, media_type="application/pdf")
