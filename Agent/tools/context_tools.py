# Agent/tools/context_tools.py
"""
Tools for retrieving resume and job description context on-demand.
This prevents context overflow by allowing the LLM to fetch these only when needed.

NOTE: These are placeholder tools. The actual content is injected by the graph's
_tools_node_callable function which has access to the state.
"""
from typing import Dict, Any
from langchain_core.tools import tool


@tool
def get_resume_text(placeholder: str = "") -> str:
    """
    Retrieve the full resume text that was uploaded by the user.
    Call this tool FIRST to access the resume content before optimization.
    
    Returns:
        The complete resume text as a string.
    """
    # Placeholder - actual content injected by graph
    return "Resume content will be provided by the system."


@tool
def get_job_description(placeholder: str = "") -> str:
    """
    Retrieve the full job description that was provided by the user.
    Call this tool FIRST to access the job description before optimization.
    
    Returns:
        The complete job description text as a string.
    """
    # Placeholder - actual content injected by graph
    return "Job description will be provided by the system."
