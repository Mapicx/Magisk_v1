# Context Tools Fix - Resume Optimization Bug

## Problem
The LLM was asking for resume and job description even though they were provided, then hitting recursion limits. This was happening because:
1. The system prompt was embedding truncated resume (2400 chars) and JD (2000 chars) text
2. This caused context overflow with Gemini's token limits
3. The LLM couldn't properly "see" the truncated content and asked for it again
4. The agent would loop infinitely trying to get the data
5. Messages weren't being accumulated in state (replaced instead of appended)

## Solution
Implemented on-demand context retrieval tools with proper state management and strict loop prevention:

### 1. New Context Tools (`Agent/tools/context_tools.py`)
- `get_resume_text`: Retrieves the FULL resume text from state (not truncated)
- `get_job_description`: Retrieves the FULL job description from state (not truncated)
- Returns plain text strings that the LLM can directly read

### 2. Fixed State Management (`Agent/graph/graph_setup.py`)
- **CRITICAL FIX**: Added `AgentState` TypedDict with `Annotated[List, operator.add]` for messages
- This ensures messages are **appended** to state instead of replaced
- Without this, tool call counts were always empty, causing infinite loops
- Added context tools to the TOOLS list
- Modified `_tools_node_callable` to inject actual content when these tools are called
- Returns formatted text: "RESUME TEXT:\n\n{full_resume}\n\n(End of resume)"
- Added strict loop prevention in `_should_continue`:
  - Stops if context tools called more than once
  - Allows up to 5 web_search calls (for keyword research)
  - Stops immediately after optimize_resume_sections is called

### 3. Updated System Prompt (`Agent/llm/llm_setup.py`)
- Removed embedded resume and JD text (was causing overflow)
- **Added explicit web search capabilities** - LLM now knows it can search for keywords
- Clear instructions that web_search is available and encouraged
- Explicit tool call order and capabilities
- Much lighter prompt (no token overflow)

### 4. Updated Backend (`Backend/routers/Resume_getter.py`)
- Added `recursion_limit: 50` to config when invoking the graph
- Allows enough iterations for: get_resume + get_jd + multiple web_searches + optimize + buffer

## Benefits
1. **No Context Overflow**: Initial prompt is minimal
2. **Full Content Access**: LLM gets FULL resume and JD (not truncated)
3. **No Infinite Loops**: Proper state management + strict limits prevent recursion errors
4. **Web Search Enabled**: LLM can now search for ATS keywords and industry trends
5. **Clearer Workflow**: Step-by-step instructions with explicit stopping conditions
6. **Better Debugging**: Tool calls are logged and visible in traces

## Testing
Run your backend:
```bash
uvicorn Backend.main:app --reload
```

Expected workflow for resume optimization:
1. LLM calls `get_resume_text` → receives full resume (4463 chars)
2. LLM calls `get_job_description` → receives full JD (1646 chars)
3. LLM analyzes and creates optimized Markdown
4. LLM calls `optimize_resume_sections` → generates PDF
5. Graph stops automatically

Expected workflow for keyword research:
1. User asks: "Find me ATS keywords"
2. LLM calls `web_search` with query like "ATS keywords for [job title]"
3. LLM analyzes search results and provides keyword suggestions
4. Graph stops automatically

## Key Technical Fix
The most critical fix was adding proper state management:
```python
class AgentState(TypedDict):
    messages: Annotated[List, operator.add]  # Appends instead of replaces!
    resume: str
    job_description: str
    resume_file_name: str
    resume_file_path: str
```

Without `Annotated[List, operator.add]`, the graph was replacing messages on each iteration, so tool call counts were always empty, causing infinite loops.

## Files Modified
- `Agent/tools/context_tools.py` (NEW)
- `Agent/graph/graph_setup.py` (MODIFIED - state management, tools, loop prevention)
- `Agent/llm/llm_setup.py` (MODIFIED - lighter prompt, web search enabled)
- `Backend/routers/Resume_getter.py` (MODIFIED - recursion_limit)
