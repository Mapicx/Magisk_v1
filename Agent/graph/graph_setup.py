# Agent/graph/graph_setup.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Annotated
from datetime import datetime
import operator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import StructuredTool
from typing_extensions import TypedDict

from Agent.llm.llm_setup import setup_llm, get_system_prompt
from Agent.tools.websearch import web_search                  # may be plain func or @tool
from Agent.tools.resume_tools import optimize_resume_sections  # in our patch it's @tool
from Agent.tools.context_tools import get_resume_text, get_job_description


# Define state schema with message accumulation
class AgentState(TypedDict):
    messages: Annotated[List, operator.add]  # This will append messages instead of replacing
    resume: str
    job_description: str
    resume_file_name: str
    resume_file_path: str
    linkedin_url: str
    github_url: str
    leetcode_url: str


def _ensure_messages(state_messages: Any) -> List[Any]:
    msgs = state_messages or []
    out: List[Any] = []
    for m in msgs:
        if isinstance(m, (HumanMessage, AIMessage, ToolMessage, SystemMessage)):
            out.append(m)
        elif isinstance(m, dict) and "role" in m and "content" in m:
            role = (m.get("role") or "").lower()
            content = m.get("content") or ""
            if role == "user":
                out.append(HumanMessage(content=content))
            elif role in ("assistant", "ai"):
                out.append(AIMessage(content=content))
            elif role == "system":
                out.append(SystemMessage(content=content))
            else:
                out.append(HumanMessage(content=str(content)))
        else:
            out.append(HumanMessage(content=str(m)))
    return out


def _synthesize_human_prompt(state: Dict[str, Any]) -> str:
    parts = []
    if isinstance(state.get("user_message"), str) and state["user_message"].strip():
        parts.append(f"User request: {state['user_message'].strip()}")
    if isinstance(state.get("job_description"), str) and state["job_description"].strip():
        parts.append("Job description has been provided.")
    if isinstance(state.get("resume_file_name"), str):
        parts.append(f"Resume file: {state['resume_file_name']}")
    if isinstance(state.get("resume"), str) and state["resume"].strip():
        parts.append("Resume text is attached in the conversation context.")
    if not parts:
        parts.append("Optimize my resume for the target role and explain the changes briefly.")
    return " ".join(parts)


def _safe_system_text(state: Dict[str, Any]) -> str:
    try:
        txt = get_system_prompt(state)
        if isinstance(txt, str) and txt.strip():
            return txt
    except Exception:
        pass
    return (
        "You are an expert AI resume optimizer. "
        "Use web_search if needed, then call optimize_resume_sections with the rewritten content. "
        "Return a concise final answer describing what you changed and why."
    )


def _final_file_ready(state: Dict[str, Any]) -> bool:
    """True if a ToolMessage from optimize_resume_sections produced an output_path."""
    messages = _ensure_messages(state.get("messages", []))
    for m in reversed(messages):
        if isinstance(m, ToolMessage) and getattr(m, "name", None) == "optimize_resume_sections":
            content = getattr(m, "content", {})
            if isinstance(content, dict) and content.get("output_path"):
                return True
    return False


# ---------- Tool coercion (handles plain functions OR already-tools) ----------
def _coerce_tool(obj, name: str, description: str) -> StructuredTool:
    """
    Return a StructuredTool.
    - If `obj` already looks like a StructuredTool (has .name and .invoke), return as-is.
    - Else, wrap the function via StructuredTool.from_function.
    """
    if hasattr(obj, "name") and hasattr(obj, "invoke"):
        return obj  # already a tool
    # must provide name & description for LangChain
    return StructuredTool.from_function(func=obj, name=name, description=description)

WEB_SEARCH = _coerce_tool(
    web_search,
    name="web_search",
    description="Search the web for the given query and return top results. Use at most once.",
)

OPTIMIZE_RESUME = _coerce_tool(
    optimize_resume_sections,
    name="optimize_resume_sections",
    description="Generate the FINAL styled PDF from complete Markdown (call exactly once).",
)

GET_RESUME = _coerce_tool(
    get_resume_text,
    name="get_resume_text",
    description="Retrieve the full resume text that was uploaded. Use this to access the resume content.",
)

GET_JD = _coerce_tool(
    get_job_description,
    name="get_job_description",
    description="Retrieve the full job description. Use this to access the JD content.",
)

TOOLS = [GET_RESUME, GET_JD, WEB_SEARCH, OPTIMIZE_RESUME]


def _agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    llm = setup_llm()
    bound = llm.bind_tools(TOOLS)

    system = SystemMessage(content=_safe_system_text(state))
    messages = _ensure_messages(state.get("messages", []))

    # Ensure at least one HumanMessage (helps Gemini)
    has_human = any(isinstance(m, HumanMessage) and (m.content or "").strip() for m in messages)
    if not has_human:
        messages = [HumanMessage(content=_synthesize_human_prompt(state))]

    ai = bound.invoke([system] + messages)
    if not isinstance(ai, AIMessage):
        ai = AIMessage(content=str(ai))
    
    return {"messages": [ai]}


def _tools_node_callable(state: Dict[str, Any]) -> Dict[str, Any]:
    tools_by_name = {t.name: t for t in TOOLS}

    messages = _ensure_messages(state.get("messages", []))
    last_ai: Optional[AIMessage] = None
    for m in reversed(messages):
        if isinstance(m, AIMessage):
            last_ai = m
            break

    out: List[ToolMessage] = []
    if last_ai and getattr(last_ai, "tool_calls", None):
        for tc in last_ai.tool_calls:
            name = tc.get("name")
            args = tc.get("args", {}) or {}
            tool_call_id = tc.get("id") or tc.get("tool_call_id")

            tool_obj = tools_by_name.get(name)
            if tool_obj is None:
                result_content = {"ok": False, "error": f"Unknown tool '{name}'"}
            else:
                # Handle context retrieval tools specially - return raw text
                if name == "get_resume_text":
                    resume = state.get("resume", "No resume provided.")
                    result_content = f"RESUME TEXT:\n\n{resume}\n\n(End of resume - {len(resume)} characters)"
                elif name == "get_job_description":
                    jd = state.get("job_description", "No job description provided.")
                    result_content = f"JOB DESCRIPTION:\n\n{jd}\n\n(End of job description - {len(jd)} characters)"
                else:
                    # Regular tool invocation
                    try:
                        result_content = tool_obj.invoke(args)
                    except Exception as e:
                        result_content = {"ok": False, "error": str(e)}

            out.append(ToolMessage(name=name, content=result_content, tool_call_id=tool_call_id))

    # Finishing hint if file is ready (helps prevent another loop)
    try:
        if any(
            (getattr(m, "name", None) == "optimize_resume_sections")
            and isinstance(getattr(m, "content", None), dict)
            and m.content.get("output_path")
            for m in out
        ):
            out.append(HumanMessage(content=(
                "The optimized resume file has been generated. "
                "Conclude with a short confirmation and do not call any more tools."
            )))
    except Exception:
        pass

    return {"messages": out}


def _should_continue(state: Dict[str, Any]) -> str:
    # Stop immediately once the final file exists
    if _final_file_ready(state):
        return END

    messages = _ensure_messages(state.get("messages", []))
    
    # Count tool calls to prevent infinite loops
    tool_call_counts = {}
    for m in messages:
        if isinstance(m, ToolMessage):
            name = getattr(m, "name", None)
            if name:
                tool_call_counts[name] = tool_call_counts.get(name, 0) + 1
    
    # Stop if we've called context tools multiple times (they should only be called once each)
    if tool_call_counts.get("get_resume_text", 0) > 1 or tool_call_counts.get("get_job_description", 0) > 1:
        return END
    
    # Allow multiple web_search calls (user might want to search for different things)
    # Only stop if excessive (more than 5 searches)
    if tool_call_counts.get("web_search", 0) > 5:
        return END
    
    # Stop if we've called optimize_resume_sections (should only happen once)
    if tool_call_counts.get("optimize_resume_sections", 0) >= 1:
        return END
    
    last_ai: Optional[AIMessage] = None
    for m in reversed(messages):
        if isinstance(m, AIMessage):
            last_ai = m
            break
    
    if last_ai and getattr(last_ai, "tool_calls", None):
        return "tools"
    
    return END


def build_graph():
    """Compile and return the LangGraph app used by the backend."""
    graph = StateGraph(AgentState)
    graph.add_node("agent", _agent_node)
    graph.add_node("tools", _tools_node_callable)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", _should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    memory = MemorySaver()
    # Recursion limit is set at invoke time, not compile time
    return graph.compile(checkpointer=memory)

