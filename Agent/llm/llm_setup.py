# Agent/llm/llm_setup.py
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Tool imports
from ..tools.resume_tools import optimize_resume_sections
from ..tools.websearch import web_search  # NEW

load_dotenv()

def setup_llm() -> ChatGoogleGenerativeAI:
    """
    Initialize Gemini model with bound tools for ReAct agent.
    Tools: resume optimization + web search.
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.1,
        streaming=True,
    )
    # Bind both tools for reasoning-acting flow
    return llm.bind_tools([optimize_resume_sections, web_search])

def get_system_prompt(state) -> str:
    """
    System prompt guiding the model on how to optimize resumes and use tools properly.
    """
    resume_text = state.get('resume', 'No resume provided.')
    jd_text = state.get('job_description', 'No job description provided.')
    resume_file_path = state.get('resume_file_path', 'No file path provided.')
    resume_file_name = state.get('resume_file_name', 'Unknown file name.')

    return f"""
You are an expert AI agent specializing in ATS-optimized resume writing and career consulting.
Your task: rewrite and optimize the user's resume for the provided job description.

TOOLS AVAILABLE:
1️⃣ optimize_resume_sections: Generates a PDF resume from Markdown.
2️⃣ web_search: Searches the web for fresh industry keywords and phrasing.

When using optimize_resume_sections:
- Arguments:
  • output_path: string (e.g. "optimized_resume.pdf")
  • optimized_markdown: string (entire resume in Markdown)
  • name, title, contact_line: strings for the header
- Use markdown headings (#, ##) for sections
- Bold skills, metrics, and key terms (**Python**, **90%**, **AWS**)
- Use bullet points (•) for achievements
- Keep format ATS-friendly (no tables/images)
- Separate roles/projects with 2 blank lines
- Never invent fake experience

Resume file: {resume_file_name}
Local path: {resume_file_path}

═══════════════════════════════════════════════════════════════════
📄 CURRENT RESUME:
{resume_text}

═══════════════════════════════════════════════════════════════════
🎯 JOB DESCRIPTION:
{jd_text}

═══════════════════════════════════════════════════════════════════
Output only one clean Markdown resume via optimize_resume_sections.
"""
