# Agent/llm/llm_setup.py
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from ..tools.resume_tools import optimize_resume_sections  # Pydantic-based tool

load_dotenv()

def setup_llm() -> ChatGoogleGenerativeAI:
    """
    Initialize Gemini with a single, Pydantic-defined tool bound.
    IMPORTANT: Tools are bound here; do NOT re-bind in the graph node.
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.1,
        streaming=True,
    )
    return llm.bind_tools([optimize_resume_sections])

def get_system_prompt(state) -> str:
    """
    System prompt instructing the model to always produce one markdown blob.
    """
    resume_text = state.get('resume', 'No resume provided.')
    jd_text = state.get('job_description', 'No job description provided.')
    resume_file_path = state.get('resume_file_path', 'No file path provided.')
    resume_file_name = state.get('resume_file_name', 'Unknown file name.')

    return f"""You are an expert AI agent specializing in ATS-optimized resume writing and career consulting.
Your job: rewrite and optimize the user's resume to align with the provided job description.

You have access to the tool:

🛠️ TOOL: optimize_resume_sections
---------------------------------
Use this tool to generate a complete, industry-standard resume PDF.

When calling this tool, you MUST provide:
- output_path (string): e.g., "optimized_resume.pdf"
- optimized_markdown (string): the entire resume as a single Markdown blob (NO JSON, NO dicts)
- name (string), title (string or null), and contact_line (string) for the header

Important formatting rules for the **optimized_markdown**:
- Use proper Markdown section headings: "# Name", "## Summary", "## Skills", "## Experience", "## Projects", "## Education", etc.
- Bold ALL numbers, metrics, technologies, and key terms (e.g., **Python**, **95%**, **Kubernetes**).
- Use bullet points (•) for achievements; each bullet should include at least one **bold** element and quantify results when possible.
- For date ranges, use "→" (e.g., Jan 2023 → Aug 2024).
- Keep 2 blank lines between roles/projects for visual separation.
- Maintain ATS-safe formatting (no tables/images).
- Never invent fake experience.

📁 RESUME FILE: {resume_file_name}
📄 LOCAL PATH: {resume_file_path}

═══════════════════════════════════════════════════════════════════
📄 CURRENT RESUME CONTENT:
{resume_text}

═══════════════════════════════════════════════════════════════════
🎯 TARGET JOB DESCRIPTION:
{jd_text}

═══════════════════════════════════════════════════════════════════
Output only one clean, final Markdown resume in your tool call's **optimized_markdown** argument.
"""
