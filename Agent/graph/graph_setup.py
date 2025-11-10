# Agent/graph/graph_setup.py
from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from ..llm.llm_setup import setup_llm, get_system_prompt
from ..models.chat_state import ChatState
from ..tools.pdf_tools import execute_resume_optimization
from ..tools.resume_tools import optimize_resume_sections
from ..tools.websearch import web_search  # NEW IMPORT
from ..utils.logging_utils import log_event

def create_agent_node():
    def agent(state: ChatState):
        llm = setup_llm()
        sys_prompt = get_system_prompt(state)
        messages = [SystemMessage(content=sys_prompt)] + state["messages"]
        response = llm.invoke(messages)
        log_event("Agent", f"LLM responded with: {response}")
        return {"messages": [response]}
    return agent

def create_tool_node():
    def tool_node(state: ChatState):
        tool_calls = state["messages"][-1].tool_calls # type: ignore
        results = []

        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = dict(tool_call["args"])

            log_event("ToolNode", f"Tool call: {tool_name}({tool_args})")

            # ---- Resume Optimizer Tool ----
            if tool_name == "optimize_resume_sections":
                if "optimized_markdown" in tool_args and "optimized_text_sections" not in tool_args:
                    tool_args["optimized_text_sections"] = tool_args.pop("optimized_markdown")
                try:
                    result = execute_resume_optimization(**tool_args)
                except TypeError as e:
                    result = (
                        f"Executor TypeError: {e}. "
                        "Expected args: output_path, optimized_text_sections, name, title (opt), "
                        "contact_line, original_file_name (opt)."
                    )

            # ---- Web Search Tool ----
            elif tool_name == "web_search":
                try:
                    result = web_search.run(tool_args)
                except Exception as e:
                    result = f'{{"error":"web_search_failed","detail":"{str(e)}"}}'

            else:
                result = f"Unknown tool: {tool_name}"

            log_event("ToolNode", f"Result: {result[:300]}")  # truncate long text
            results.append(ToolMessage(content=result, tool_call_id=tool_call["id"], name=tool_name))

        return {"messages": results}
    return tool_node

def should_continue(state: ChatState):
    messages = state["messages"]
    last = messages[-1]
    if hasattr(last, "tool_calls") and last.tool_calls: # type: ignore
        return "tools"
    return END

def setup_graph():
    builder = StateGraph(ChatState)
    memory = MemorySaver()

    builder.add_node("agent", create_agent_node())
    builder.add_node("tools", create_tool_node())

    builder.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")
    builder.set_entry_point("agent")

    log_event("Graph", "Graph setup complete with tools: optimize_resume_sections, web_search")
    return builder.compile(checkpointer=memory)
