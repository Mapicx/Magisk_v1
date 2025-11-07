# Backend/routers/Resume_getter.py
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from supabase import create_client, Client
from Backend import models, database
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import fitz
from langchain_core.messages import HumanMessage
import uuid, os, sys
from pathlib import Path
import io
import logging

# Create router logger
router_logger = logging.getLogger("Resume_Router")
router_logger.setLevel(logging.INFO)

# ---------- SETUP ABSOLUTE IMPORTS ----------
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from Agent.graph.graph_setup import setup_graph
    from Agent.tools.pdf_tools import optimize_resume_sections
    from Agent.utils.logging_utils import log_llm_operation
    from Agent.models.chat_state import ChatState
except ImportError as e:
    router_logger.error(f"Import error: {e}")
    raise

router = APIRouter(tags=["Resume Optimization"])

# ---------- SETUP ----------
load_dotenv(project_root / ".env")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Missing Supabase credentials in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

LOCAL_RESUMES_DIR = project_root / "local_resumes"
LOCAL_RESUMES_DIR.mkdir(exist_ok=True)
OPTIMIZED_RESUMES_DIR = project_root / "optimized_resumes"
OPTIMIZED_RESUMES_DIR.mkdir(exist_ok=True)

# Use the new hybrid tool
tools = [optimize_resume_sections]
chatbot = setup_graph()

router_logger.info("Resume router initialized successfully")


# ---------- MAIN ROUTE ----------
@router.post("/optimize_resume")
async def optimize_resume(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    user_message: str = Form(...),
    thread_id: str = Form(None),
    db: Session = Depends(database.get_db)
):
    """Main endpoint for resume optimization"""
    
    router_logger.info(f"Optimize resume endpoint called - File: {file.filename}, Thread: {thread_id or 'NEW'}")
    
    # Step 1: Validate file
    if not file.filename or not file.filename.endswith(".pdf"):
        router_logger.error("Validation failed: Not a PDF file")
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # Step 2: Read file bytes
    try:
        file_bytes = await file.read()
        router_logger.info(f"File read successfully: {len(file_bytes)} bytes")
    except Exception as e:
        router_logger.error(f"Failed to read file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")

    # Step 3: Upload to Supabase and save locally
    unique_name = f"resumes/{uuid.uuid4()}_{file.filename}"
    
    try:
        supabase.storage.from_("resumes").upload(unique_name, file_bytes)
        router_logger.info(f"File uploaded to Supabase: {unique_name}")
    except Exception as e:
        router_logger.error(f"Supabase upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    public_url = supabase.storage.from_("resumes").get_public_url(unique_name)

    local_file_path = LOCAL_RESUMES_DIR / f"{uuid.uuid4()}_{file.filename}"
    try:
        with open(local_file_path, "wb") as f:
            f.write(file_bytes)
        log_llm_operation("RESUME_SAVED_LOCALLY", {
            "file_path": str(local_file_path),
            "file_size": len(file_bytes),
            "thread_id": thread_id or "new_session"
        })
    except Exception as e:
        router_logger.error(f"Local file save failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Local file save failed: {str(e)}")

    # Step 4: Extract text from PDF
    try:
        resume_text = ""
        file_buffer = io.BytesIO(file_bytes)
        with fitz.open(stream=file_buffer, filetype="pdf") as doc:
            page_count = doc.page_count
            for page in doc:
                resume_text += page.get_text() # type: ignore
        resume_text = resume_text.strip()
        
        log_llm_operation("RESUME_TEXT_EXTRACTED", {
            "text_length": len(resume_text),
            "pages": page_count,
            "thread_id": thread_id or "new_session"
        })

    except Exception as e:
        router_logger.error(f"Text extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {str(e)}")

    # Step 5: Save to database
    resume_entry = models.Resume(filename=unique_name, file_url=public_url) # type: ignore
    db.add(resume_entry)
    db.commit()
    db.refresh(resume_entry)
    router_logger.info(f"Resume saved to database with ID: {resume_entry.id}")

    # Step 6: LLM Processing
    try:
        config_thread_id = thread_id or str(uuid.uuid4())
        config = {"configurable": {"thread_id": config_thread_id}}
        session_type = "existing_session" if thread_id else "new_session"

        inputs = {
            "messages": [HumanMessage(content=user_message)],
            "resume": resume_text,
            "job_description": job_description,
            "resume_file_path": str(local_file_path),
            "resume_file_name": file.filename
        }

        log_llm_operation("CHATBOT_INVOCATION_START", {
            "thread_id": config_thread_id,
            "session_type": session_type,
            "user_message_length": len(user_message),
            "resume_length": len(resume_text),
            "jd_length": len(job_description)
        })

        result = chatbot.invoke(inputs, config=config) # type: ignore

        ai_response = ""
        tool_used = False
        
        # Parse LLM response
        for message in reversed(result["messages"]):
            if hasattr(message, "content") and message.content:
                ai_response = message.content
                if (hasattr(message, "tool_calls") and message.tool_calls) or \
                   (hasattr(message, "tool_call_id") and message.tool_call_id):
                    tool_used = True
                break

        # Log the complete AI response
        log_llm_operation("LLM_RESPONSE_COMPLETE", {
            "thread_id": config_thread_id,
            "session_type": session_type,
            "ai_response": ai_response,  # Full response logged
            "ai_response_length": len(ai_response),
            "tool_used": tool_used,
            "total_messages": len(result["messages"])
        })

    except Exception as e:
        log_llm_operation("CHATBOT_INVOCATION_ERROR", {
            "error": str(e),
            "thread_id": config_thread_id if 'config_thread_id' in locals() else "unknown", # type: ignore
            "session_type": session_type if 'session_type' in locals() else "unknown" # type: ignore
        }, success=False)
        raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")

    # Step 7: Build response
    response_data = {
        "thread_id": config_thread_id,
        "session_type": session_type,
        "resume_id": resume_entry.id,
        "file_url": resume_entry.file_url,
        "local_file_path": str(local_file_path),
        "extracted_resume_text": resume_text[:500] + "..." if len(resume_text) > 500 else resume_text,
        "job_description": job_description,
        "user_message": user_message,
        "ai_response": ai_response,
        "tool_used": tool_used
    }

    # Check for optimized resume path
    if tool_used and "saved at:" in ai_response.lower():
        import re
        path_match = re.search(r"saved at:\s*(.+\.pdf)", ai_response, re.IGNORECASE)
        if path_match:
            optimized_path = path_match.group(1)
            response_data["optimized_resume_path"] = optimized_path
            if Path(optimized_path).exists():
                response_data["optimized_file_exists"] = True
                response_data["optimized_file_name"] = Path(optimized_path).name
                router_logger.info(f"Optimized resume created: {Path(optimized_path).name}")

    router_logger.info(f"Request completed successfully - Thread: {config_thread_id}")
    
    return response_data


# ---------- SESSION MANAGEMENT ROUTES ----------
@router.get("/session_info/{thread_id}")
async def get_session_info(thread_id: str):
    """Get information about a session thread"""
    router_logger.info(f"Session info requested for thread: {thread_id}")
    try:
        session_exists = True
        return {
            "thread_id": thread_id,
            "session_exists": session_exists,
            "message": "Session tracking is basic. For production, consider using a persistent checkpointer."
        }
    except Exception as e:
        router_logger.error(f"Error checking session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error checking session: {str(e)}")


@router.post("/new_session")
async def create_new_session():
    """Explicitly create a new session and return the thread_id"""
    new_thread_id = str(uuid.uuid4())
    
    log_llm_operation("NEW_SESSION_CREATED", {
        "thread_id": new_thread_id
    })
    
    return {
        "thread_id": new_thread_id,
        "message": "New session created successfully"
    }


# ---------- OTHER ROUTES ----------
@router.get("/optimized_resumes")
async def list_optimized_resumes():
    """List all optimized resumes"""
    router_logger.info("Listing optimized resumes")
    try:
        optimized_files = []
        for file_path in OPTIMIZED_RESUMES_DIR.glob("*.pdf"):
            optimized_files.append({
                "filename": file_path.name,
                "file_path": str(file_path),
                "size": file_path.stat().st_size,
                "created": file_path.stat().st_ctime
            })

        router_logger.info(f"Found {len(optimized_files)} optimized resumes")
        return {
            "optimized_resumes": optimized_files,
            "total_count": len(optimized_files)
        }
    except Exception as e:
        router_logger.error(f"Error listing optimized resumes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing optimized resumes: {str(e)}")


@router.get("/download_optimized/{filename}")
async def download_optimized_resume(filename: str):
    """Download an optimized resume"""
    router_logger.info(f"Download requested: {filename}")
    try:
        file_path = OPTIMIZED_RESUMES_DIR / filename

        if not file_path.exists():
            router_logger.error(f"File not found: {filename}")
            raise HTTPException(status_code=404, detail="File not found")

        router_logger.info(f"Serving file: {filename}")
        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/pdf"
        )
    except Exception as e:
        router_logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")