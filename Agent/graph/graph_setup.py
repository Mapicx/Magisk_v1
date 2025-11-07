# Agent/graph/graph_setup.py
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import ToolMessage, SystemMessage, AIMessage

from ..models.chat_state import ChatState
from ..llm.llm_setup import setup_llm, get_system_prompt
from ..tools.pdf_tools import execute_resume_optimization
from ..utils.logging_utils import log_llm_operation

def create_agent_node():
    llm = setup_llm()
    def agent_node(state: ChatState):
        log_llm_operation("LLM_PROCESSING_START", {
            "message_count": len(state["messages"]),
            "resume_provided": bool(state.get("resume")),
            "jd_provided": bool(state.get("job_description")),
            "file_path": state.get("resume_file_path"),
        })
        system_prompt = SystemMessage(content=get_system_prompt(state))
        messages_with_prompt = [system_prompt] + state["messages"]

        last_user_message = None
        for msg in reversed(state["messages"]):
            if hasattr(msg, "content"):
                last_user_message = msg.content
                break
        log_llm_operation("LLM_INVOCATION_START", {
            "user_query": (last_user_message[:100] + "..." if last_user_message and len(last_user_message) > 100 else last_user_message),
            "total_tokens_estimate": len(str(messages_with_prompt)) // 4,
        })

        try:
            response = llm.invoke(messages_with_prompt)
            response_content = response.content or ""
            tool_calls_count = len(response.tool_calls) if hasattr(response, "tool_calls") else 0
            log_llm_operation("LLM_RESPONSE_GENERATED", {
                "response_content": response_content,
                "response_length": len(response_content),
                "tool_calls": tool_calls_count,
            })
            return {"messages": [response]}
        except Exception as e:
            log_llm_operation("LLM_INVOCATION_ERROR", {"error": str(e), "messages_count": len(messages_with_prompt)}, success=False)
            return {"messages": [AIMessage(content=f"Sorry, I encountered an error: {str(e)}")]}

    return agent_node

def create_tool_node():
    def tool_node(state: ChatState):
        messages = state["messages"]
        last_message = messages[-1]
        tool_calls = getattr(last_message, "tool_calls", [])
        results = []

        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = dict(tool_call["args"])  # copy

            # pass original filename so pdf_tools can construct "<name>_optimised_<uuid>.pdf"
            original_name = state.get("resume_file_name") or None
            if original_name:
                tool_args["original_file_name"] = original_name

            # log args
            tool_args_with_previews = {}
            for key, value in tool_args.items():
                if isinstance(value, str):
                    prev = value[:500] + "..." if len(value) > 500 else value
                    tool_args_with_previews[key] = {"length": len(value), "preview": prev, "full_content": value}
                else:
                    tool_args_with_previews[key] = value
            log_llm_operation("TOOL_EXECUTION_START", {
                "tool_name": tool_name,
                "tool_args_keys": list(tool_args.keys()),
                "tool_args_full": tool_args_with_previews
            })

            for key, value in tool_args.items():
                if isinstance(value, str) and value.strip():
                    log_llm_operation(f"TOOL_ARG_{key.upper()}", {
                        "tool_name": tool_name,
                        "section": key,
                        "content_length": len(value),
                        "content_preview": value[:300] + "..." if len(value) > 300 else value
                    })

            if tool_name == "optimize_resume_sections":
                # map new -> old content param if needed
                if "optimized_markdown" in tool_args and "optimized_text_sections" not in tool_args:
                    tool_args["optimized_text_sections"] = tool_args.pop("optimized_markdown")
                try:
                    # Do NOT pass `state` (executor doesn’t need it)
                    result = execute_resume_optimization(**tool_args)
                except TypeError as e:
                    result = (
                        f"Executor TypeError: {e}. "
                        "Hint: execute_resume_optimization(...) must accept: "
                        "output_path, optimized_text_sections, name, contact_line, title (optional), original_file_name (optional)."
                    )
            else:
                result = f"Unknown tool: {tool_name}"

            results.append(ToolMessage(content=result, tool_call_id=tool_call["id"], name=tool_name))
            log_llm_operation("TOOL_EXECUTION_COMPLETE", {
                "tool_name": tool_name,
                "result": result,
                "result_length": len(result),
            })

        return {"messages": results}
    return tool_node

def should_continue(state: ChatState) -> Literal["tools", "__end__"]:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:  # type: ignore[attr-defined]
        return "tools"
    return "__end__"

def setup_graph():
    checkpoint = MemorySaver()
    graph = StateGraph(ChatState)
    graph.add_node("agent", create_agent_node())
    graph.add_node("tools", create_tool_node())
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "__end__": END})
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=checkpoint)
