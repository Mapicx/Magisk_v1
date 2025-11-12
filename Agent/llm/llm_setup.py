# Agent/llm/llm_setup.py
import os
from dotenv import load_dotenv
from typing import Any, Dict
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

def setup_llm() -> ChatGoogleGenerativeAI:
    """
    Return the UNBOUND Gemini model.
    Tools are bound inside the graph, not here.
    """
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.1,
        streaming=True,
    )

def get_system_prompt(state: Dict[str, Any]) -> str:
    resume_file_name = state.get('resume_file_name', 'Unknown file name.')
    resume_file_path = state.get('resume_file_path', 'No file path provided.')
    
    # Check if resume and JD are available
    has_resume = bool(state.get('resume'))
    has_jd = bool(state.get('job_description'))
    
    # Get profile URLs
    linkedin_url = state.get('linkedin_url', '')
    github_url = state.get('github_url', '')
    leetcode_url = state.get('leetcode_url', '')
    
    # Build profile URLs section
    profile_urls_text = ""
    if linkedin_url or github_url or leetcode_url:
        profile_urls_text = "\n\nPROFILE URLs PROVIDED:"
        if linkedin_url:
            profile_urls_text += f"\n- LinkedIn: {linkedin_url}"
        if github_url:
            profile_urls_text += f"\n- GitHub: {github_url}"
        if leetcode_url:
            profile_urls_text += f"\n- LeetCode: {leetcode_url}"
        profile_urls_text += "\n\nIMPORTANT: You MUST include these URLs in the contact section of the optimized resume!"

    return f"""You are an expert ATS-focused resume optimizer. Your job is to ALWAYS generate an optimized PDF resume.

AVAILABLE TOOLS:
1. get_resume_text - Retrieve the uploaded resume
2. get_job_description - Retrieve the job description
3. web_search - Search for ATS keywords and industry trends (optional)
4. optimize_resume_sections - Generate the final PDF from Markdown (REQUIRED - YOU MUST CALL THIS!)

MANDATORY WORKFLOW - FOLLOW EXACTLY:
1. Call get_resume_text to retrieve the resume
2. Call get_job_description to retrieve the job description
3. (Optional) Call web_search for additional ATS keywords if needed
4. Analyze both documents and create optimized Markdown content
5. **YOU MUST CALL optimize_resume_sections** with these parameters:
   - optimized_markdown: Complete resume in Markdown format with all sections
   - name: Candidate's full name
   - title: Professional title/headline
   - contact_line: Email, phone, location, AND profile URLs formatted as "Label: URL" (e.g., "LinkedIn: https://linkedin.com/in/username | GitHub: https://github.com/username"){profile_urls_text}
   - output_path: Leave empty (auto-generated)

CRITICAL RULES:
- You MUST call optimize_resume_sections to generate the PDF - this is NOT optional!
- Never just describe changes - ALWAYS generate the actual PDF
- Include ALL resume sections: Summary, Experience, Education, Skills, etc.
- Use Markdown format: # for name, ## for sections, • for bullets, **bold** for emphasis
- Keep it 1-2 pages, ATS-friendly (no tables/images)
- Never fabricate experience or skills
- **ALWAYS include profile URLs in contact_line if provided**
- **FORMAT URLs AS LABELS**: Use "LinkedIn: URL" format, NOT just the URL. The PDF will show "LinkedIn" as a clickable link, not the full URL

MARKDOWN FORMAT EXAMPLE:
```
# John Doe
## Professional Summary
Experienced software engineer...

## Experience
**Senior Engineer** - Company Name (2020-Present)
• Achievement with **metrics**
• Another achievement

## Skills
**Languages:** Python, Java, JavaScript
**Frameworks:** React, Django, TensorFlow
```

Resume file: {resume_file_name}
Resume ready: {has_resume}
JD ready: {has_jd}

REMEMBER: You MUST call optimize_resume_sections at the end to generate the PDF file!"""
