# Agent/tools/resume_tools.py
from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import tool

class OptimizeResumeInput(BaseModel):
    """
    Minimal, Gemini-safe schema (no anyOf/oneOf/additionalProperties).
    The model must return a single markdown string with the whole resume.
    """
    output_path: str = Field(..., description="Output PDF file name, e.g., 'optimized_resume.pdf'.")
    optimized_markdown: str = Field(
        ...,
        description="Complete, formatted resume in Markdown (single blob)."
    )
    name: str = Field(..., description="Full name of the candidate.")
    contact_line: str = Field(..., description="Contact details (email, phone, LinkedIn, etc.).")
    title: Optional[str] = Field(None, description="Professional title or role; may be null.")

@tool("optimize_resume_sections", args_schema=OptimizeResumeInput)
def optimize_resume_sections(
    output_path: str,
    optimized_markdown: str,
    name: str,
    contact_line: str,
    title: Optional[str] = None,
) -> str:
    """
    Declaration-only tool for the LLM. The actual PDF generation is executed inside the ToolNode
    via your execute_resume_optimization(...) function.
    """
    # This return is a harmless fallback if someone calls the tool locally.
    return f"Queued resume optimization for {name}. Target file: {output_path}"
